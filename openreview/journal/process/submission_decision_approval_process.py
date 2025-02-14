def process(client, edit, invitation):

    journal = openreview.journal.Journal()
    venue_id = journal.venue_id

    decision_approval = client.get_note(edit.note.id)
    decision = client.get_note(edit.note.replyto)

    ## On update or delete return
    if decision_approval.tcdate != decision_approval.tmdate:
        return

    submission = client.get_note(decision.forum)

    ## Make the decision public
    print('Make decision public')
    invitation = journal.invitation_builder.post_invitation_edit(invitation=Invitation(id=journal.get_release_decision_id(number=submission.number),
            bulk=True,
            invitees=[venue_id],
            readers=['everyone'],
            writers=[venue_id],
            signatures=[venue_id],
            edit={
                'signatures': { 'const': [venue_id ] },
                'readers': { 'const': [ venue_id, journal.get_action_editors_id(number=submission.number) ] },
                'writers': { 'const': [ venue_id ] },
                'note': {
                    'id': { 'withInvitation': journal.get_ae_decision_id(number=submission.number) },
                    'readers': { 'const': [ 'everyone' ] },
                    'nonreaders': { 'const': [] }
                }
            }
    ))

    print('Check rejection')
    print(decision.content)
    if decision.content['recommendation']['value'] == 'Reject':
        ## Post a reject edit
        client.post_note_edit(invitation=journal.get_rejected_id(),
            signatures=[venue_id],
            note=openreview.api.Note(
                id=submission.id,
                content={
                    '_bibtex': {
                        'value': journal.get_bibtex(submission, journal.rejected_venue_id, anonymous=True)
                    }
                }
            )
        )
        return

    ## Make submission editable by the authors
    print('Make submission editable by the authors')
    invitation = journal.invitation_builder.post_invitation_edit(invitation=Invitation(id=journal.get_submission_editable_id(number=submission.number),
            #bulk=True,
            invitees=[venue_id],
            noninvitees=[journal.get_editors_in_chief_id()],
            readers=[venue_id],
            writers=[venue_id],
            signatures=[venue_id],
            edit={
                'signatures': { 'const': [venue_id ] },
                'readers': { 'const': [ venue_id, journal.get_action_editors_id(number=submission.number), journal.get_authors_id(number=submission.number) ] },
                'writers': { 'const': [ venue_id ] },
                'note': {
                    'id': { 'const': submission.id },
                    'writers': { 'const': [ venue_id, journal.get_authors_id(number=submission.number) ] }
                }
            }
    ))

    client.post_note_edit(invitation=journal.get_submission_editable_id(number=submission.number),
        signatures=[venue_id],
        note=openreview.api.Note(
            id=submission.id
        )
    )

    ## Enable Camera Ready Revision
    print('Enable Camera Ready Revision')
    journal.invitation_builder.set_camera_ready_revision_invitation(submission, decision, journal.get_due_date(weeks = 4))

    ## Send email to authors
    print('Send email to authors')
    if decision.content['recommendation']['value'] == 'Accept as is':
        client.post_message(
            recipients=[journal.get_authors_id(number=submission.number)],
            subject=f'''[{journal.short_name}] Decision for your {journal.short_name} submission {submission.content['title']['value']}''',
            message=f'''Hi {{{{fullname}}}},

We are happy to inform you that, based on the evaluation of the reviewers and the recommendation of the assigned Action Editor, your {journal.short_name} submission title "{submission.content['title']['value']}" is accepted as is.

To know more about the decision and submit the deanonymized camera ready version of your manuscript, please follow this link and click on button "Camera Ready Revision": https://openreview.net/forum?id={submission.id}

In addition to your final manuscript, we strongly encourage you to submit a link to 1) code associated with your and 2) a short video presentation of your work. You can provide these links to the corresponding entries on the revision page.

For more details and guidelines on the {journal.short_name} review process, visit {journal.website}.

We thank you for your contribution to {journal.short_name} and congratulate you for your successful submission!

The {journal.short_name} Editors-in-Chief
''',
            replyTo=journal.contact_info
        )
        return

    if decision.content['recommendation']['value'] == 'Accept with minor revision':
        client.post_message(
            recipients=[journal.get_authors_id(number=submission.number)],
            subject=f'''[{journal.short_name}] Decision for your {journal.short_name} submission {submission.content['title']['value']}''',
            message=f'''Hi {{{{fullname}}}},

We are happy to inform you that, based on the evaluation of the reviewers and the recommendation of the assigned Action Editor, your {journal.short_name} submission title "{submission.content['title']['value']}" is accepted with minor revision.

To know more about the decision and submit the deanonymized camera ready version of your manuscript, please follow this link and click on button "Camera Ready Revision": https://openreview.net/forum?id={submission.id}

The Action Editor responsible for your submission will have provided a description of the revision expected for accepting your final manuscript.

In addition to your final manuscript, we strongly encourage you to submit a link to 1) code associated with your and 2) a short video presentation of your work. You can provide these links to the corresponding entries on the revision page.

For more details and guidelines on the {journal.short_name} review process, visit {journal.website}.

We thank you for your contribution to {journal.short_name} and congratulate you for your successful submission!

The {journal.short_name} Editors-in-Chief
''',
            replyTo=journal.contact_info
        )
