def process_update(client, edge, invitation, existing_edge):
    latest_edge = client.get_edge(edge.id,True)
    if latest_edge.ddate and not edge.ddate:
        # edge has been removed
        return

    journal = openreview.journal.Journal()

    venue_id = journal.venue_id
    note = client.get_note(edge.head)
    group = client.get_group(journal.get_reviewers_id(number=note.number))
    tail_assignment_edges = client.get_edges(invitation=journal.get_reviewer_assignment_id(), tail=edge.tail)
    head_assignment_edges = client.get_edges(invitation=journal.get_reviewer_assignment_id(), head=edge.head)
    submission_edges = client.get_edges(invitation=journal.get_reviewer_assignment_id(number=note.number))
    responsiblity_invitation_edit = None

    ## Check task completion
    if len(head_assignment_edges) >= 3:
        if not submission_edges:
            print('Mark task a complete')
            client.post_edge(openreview.api.Edge(invitation=journal.get_reviewer_assignment_id(number=note.number),
                readers = [venue_id, journal.get_action_editors_id(number=note.number)],
                nonreaders = [journal.get_authors_id(number=note.number)],
                writers = [venue_id],
                signatures = [journal.get_action_editors_id(number=note.number)],
                head = note.id,
                tail = journal.get_reviewers_id(),
                weight = 1
            ))
    else:
        if submission_edges:
            print('Mark task as uncomplete')
            submission_edge = submission_edges[0]
            submission_edge.ddate = openreview.tools.datetime_millis(datetime.datetime.utcnow())
            client.post_edge(submission_edge)

    ## Enable reviewer responsibility task
    if len(tail_assignment_edges) == 1 and not edge.ddate:
        print('Enable reviewer responsibility task for', edge.tail)
        responsiblity_invitation_edit = client.post_invitation_edit(invitations=journal.get_reviewer_responsibility_id(),
            params={ 'reviewerId': edge.tail, 'duedate': openreview.tools.datetime_millis(journal.get_due_date(weeks = 1)) },
            readers=[venue_id],
            writers=[venue_id],
            signatures=[venue_id]
        )

    pending_review_edges = client.get_edges(invitation=journal.get_reviewer_pending_review_id(), tail=edge.tail)
    pending_review_edge = None
    if pending_review_edges:
        pending_review_edge = pending_review_edges[0]

    ## Unassignment action
    if edge.ddate and edge.tail in group.members:
        print(f'Remove member {edge.tail} from {group.id}')
        client.remove_members_from_group(group.id, edge.tail)

        recipients=[edge.tail]
        subject=f'[{journal.short_name}] You have been unassigned from {journal.short_name} submission {note.content["title"]["value"]}'

        message=f'''Hi {{{{fullname}}}},

We recently informed you that your help was requested to review a {journal.short_name} submission titled "{note.content['title']['value']}".

However, it was just determined that your help is no longer needed for this submission and you have been unassigned as a reviewer for it.

If you have any questions, don’t hesitate to reach out directly to the Action Editor (AE) for the submission, for example by leaving a comment readable by the AE only, on the OpenReview page for the submission: https://openreview.net/forum?id={note.id}

Apologies for the change and thank you for your continued involvement with {journal.short_name}!

The {journal.short_name} Editors-in-Chief
'''

        client.post_message(subject, recipients, message)

        if pending_review_edge and pending_review_edge.weight > 0:
            pending_review_edge.weight -= 1
            client.post_edge(pending_review_edge)


        print('Disable assignment acknowledgement task for', edge.tail)
        journal.invitation_builder.expire_invitation(journal.get_reviewer_assignment_acknowledgement_id(number=note.number, reviewer_id=edge.tail))

        return

    ## Assignment action
    if not edge.ddate and edge.tail not in group.members:
        print(f'Add member {edge.tail} to {group.id}')
        client.add_members_to_group(group.id, edge.tail)

        if pending_review_edge:
            pending_review_edge.weight += 1
            client.post_edge(pending_review_edge)
        else:
            client.post_edge(openreview.api.Edge(invitation = journal.get_reviewer_pending_review_id(),
                readers = [venue_id, journal.get_action_editors_id(), edge.tail],
                writers = [venue_id],
                signatures = [venue_id],
                head = journal.get_reviewers_id(),
                tail = edge.tail,
                weight = 1
            ))

        review_period_length = journal.get_review_period_length(note)
        duedate = journal.get_due_date(weeks = review_period_length)

        ## Update review invitation duedate
        invitation = journal.invitation_builder.post_invitation_edit(invitation=Invitation(id=journal.get_review_id(number=note.number),
                signatures=[journal.get_editors_in_chief_id()],
                duedate=openreview.tools.datetime_millis(duedate)
        ))

        print('Enable assignment acknowledgement task for', edge.tail)
        ack_invitation_edit = client.post_invitation_edit(invitations=journal.get_reviewer_assignment_acknowledgement_id(),
            params={
                'noteId': note.id,
                'noteNumber': note.number,
                'reviewerId': edge.tail,
                'duedate': openreview.tools.datetime_millis(journal.get_due_date(days = 2)),
                'reviewDuedate': duedate.strftime("%b %d, %Y")
             },
            readers=[venue_id],
            writers=[venue_id],
            signatures=[venue_id]
        )

        recipients = [edge.tail]
        ignoreRecipients = [journal.get_solicit_reviewers_id(number=note.number)]
        subject=f'''[{journal.short_name}] Assignment to review new {journal.short_name} submission {note.content['title']['value']}'''
        message=f'''Hi {{{{fullname}}}},

With this email, we request that you submit, within {review_period_length} weeks ({duedate.strftime("%b %d")}) a review for your newly assigned {journal.short_name} submission "{note.content['title']['value']}". If the submission is longer than 12 pages (excluding any appendix), you may request more time to the AE.

Please acknowledge on OpenReview that you have received this review assignment by following this link: https://openreview.net/forum?id={note.id}&invitationId={ack_invitation_edit['invitation']['id']}

As a reminder, reviewers are **expected to accept all assignments** for submissions that fall within their expertise and annual quota (6 papers). Acceptable exceptions are 1) if you have an active, unsubmitted review for another {journal.short_name} submission or 2) situations where exceptional personal circumstances (e.g. vacation, health problems) render you incapable of performing your reviewing duties. Based on the above, if you think you should not review this submission, contact your AE directly (you can do so by leaving a comment on OpenReview, with only the Action Editor as Reader).

To submit your review, please follow this link: https://openreview.net/forum?id={note.id}&invitationId={journal.get_review_id(number=note.number)} or check your tasks in the Reviewers Console: https://openreview.net/group?id={journal.venue_id}/Reviewers#reviewer-tasks

Once submitted, your review will become privately visible to the authors and AE. Then, as soon as 3 reviews have been submitted, all reviews will become publicly visible. For more details and guidelines on performing your review, visit {journal.website}.

We thank you for your essential contribution to {journal.short_name}!

The {journal.short_name} Editors-in-Chief
'''

        client.post_message(subject, recipients, message, ignoreRecipients=ignoreRecipients, parentGroup=group.id, replyTo=journal.contact_info)

    if responsiblity_invitation_edit is not None:

        print('Send email to the reviewer')
        recipients = [edge.tail]
        ignoreRecipients = []
        subject=f'''[{journal.short_name}] Acknowledgement of Reviewer Responsibility'''
        message=f'''Hi {{{{fullname}}}},

{journal.short_name} operates somewhat differently to other journals and conferences. As a new reviewer, we'd like you to read and acknowledge some critical points of {journal.short_name} that might differ from your previous reviewing experience.

To perform this quick task, simply visit the following link: https://openreview.net/forum?id={responsiblity_invitation_edit['invitation']['edit']['note']['forum']['const']}&invitationId={responsiblity_invitation_edit['invitation']['id']}

We thank you for your essential contribution to {journal.short_name}!

The {journal.short_name} Editors-in-Chief
'''
        client.post_message(subject, recipients, message, ignoreRecipients=ignoreRecipients, parentGroup=group.id, replyTo=journal.contact_info)

