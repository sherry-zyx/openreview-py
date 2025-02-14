def process_update(client, note, invitation, existing_note):
    from datetime import datetime
    CONFERENCE_ID = ''
    CONFERENCE_SHORT_NAME = ''
    CONFERENCE_NAME = ''
    CONFERENCE_YEAR = ''
    PAPER_AUTHORS_ID = ''
    PAPER_REVIEWERS_ID = ''
    PAPER_AREA_CHAIRS_ID = ''
    PAPER_SENIOR_AREA_CHAIRS_ID = ''
    PROGRAM_CHAIRS_ID = ''
    WITHDRAWN_SUBMISSION_ID = ''
    BLIND_SUBMISSION_ID = ''
    SUBMISSION_READERS = []
    REVEAL_AUTHORS_ON_WITHDRAW = False
    REVEAL_SUBMISSIONS_ON_WITHDRAW = False
    EMAIL_PROGRAM_CHAIRS = False
    HIDE_FIELDS = []

    committee = [PAPER_AUTHORS_ID, PAPER_REVIEWERS_ID]
    if PAPER_AREA_CHAIRS_ID:
        committee.append(PAPER_AREA_CHAIRS_ID)
    if PAPER_SENIOR_AREA_CHAIRS_ID:
        committee.append(PAPER_SENIOR_AREA_CHAIRS_ID)
    committee.append(PROGRAM_CHAIRS_ID)

    forum_note = client.get_note(note.forum)

    if note.ddate:
        ## Undo withdraw submission
        print('undo withdraw submission')
        if forum_note.invitation == WITHDRAWN_SUBMISSION_ID:
            forum_note.invitation = BLIND_SUBMISSION_ID
            if forum_note.original:
                print('is double blind')
                forum_note.content = {
                    'authors': ['Anonymous'],
                    'authorids': [PAPER_AUTHORS_ID],
                    # '_bibtex': bibtex Solve this later
                }
                for field in HIDE_FIELDS:
                    forum_note.content[field] = ''

            forum_note.readers = SUBMISSION_READERS
            forum_note = client.post_note(forum_note)

            # Restore review, meta-review and decision invitations
            invitation_regex = CONFERENCE_ID + '/Paper' + str(
                forum_note.number) + '/-/(Official_Review|Meta_Review|Decision|Revision|Desk_Reject|Withdraw|Supplementary_Material|Official_Comment|Public_Comment)$'
            all_paper_invitations = openreview.tools.iterget_invitations(client, regex=invitation_regex, expired=True)
            for invitation in all_paper_invitations:
                invitation.expdate = None
                client.post_invitation(invitation)

            client.add_members_to_group(CONFERENCE_ID + '/Authors', PAPER_AUTHORS_ID)
    else:
        forum_note.invitation = WITHDRAWN_SUBMISSION_ID
        original_note = None
        if forum_note.original:
            original_note = client.get_note(id=forum_note.original)

        if REVEAL_SUBMISSIONS_ON_WITHDRAW:
            forum_note.readers = ['everyone']
        else:
            forum_note.readers = committee

        bibtex = openreview.tools.generate_bibtex(
            note=original_note if original_note is not None else forum_note,
            venue_fullname=CONFERENCE_NAME,
            url_forum=forum_note.id,
            paper_status='rejected',
            year=CONFERENCE_YEAR,
            anonymous=not(REVEAL_AUTHORS_ON_WITHDRAW),
            baseurl='https://openreview.net')

        if original_note:
            if REVEAL_AUTHORS_ON_WITHDRAW:
                forum_note.content = {
                    '_bibtex': bibtex,
                    'venue': '',
                    'venueid': ''
                }
            else:
                forum_note.content = {
                    'authors': ['Anonymous'],
                    'authorids': ['Anonymous'],
                    '_bibtex': bibtex,
                    'venue': '',
                    'venueid': ''
                }
        else:
            forum_note.content['_bibtex'] = bibtex
            forum_note.content['venue'] = ''
            forum_note.content['venueid'] = ''

        for field in HIDE_FIELDS:
            forum_note.content[field] = ''

        forum_note = client.post_note(forum_note)

        # Expire review, meta-review and decision invitations
        invitation_regex = CONFERENCE_ID + '/Paper' + str(forum_note.number) + '/-/(Official_Review|Meta_Review|Decision|Revision|Supplementary_Material|Official_Comment|Public_Comment)$'
        all_paper_invitations = client.get_all_invitations(regex=invitation_regex)
        now = openreview.tools.datetime_millis(datetime.utcnow())
        for invitation in all_paper_invitations:
            invitation.expdate = now
            client.post_invitation(invitation)

        client.remove_members_from_group(CONFERENCE_ID + '/Authors', PAPER_AUTHORS_ID)
        client.remove_members_from_group(CONFERENCE_ID + '/Authors/Accepted', PAPER_AUTHORS_ID)

    # Mail Authors, Reviewers, ACs (if present) and PCs
    action = 'restored' if note.ddate else 'withdrawn'
    email_subject = '''{CONFERENCE_SHORT_NAME}: Paper #{paper_number} {action} by paper authors'''.format(
        CONFERENCE_SHORT_NAME=CONFERENCE_SHORT_NAME,
        paper_number=forum_note.number,
        action=action
    )
    email_body = '''The {CONFERENCE_SHORT_NAME} paper "{paper_title_or_num}" has been {action} by the paper authors.'''.format(
        CONFERENCE_SHORT_NAME=CONFERENCE_SHORT_NAME,
        paper_title_or_num=forum_note.content.get('title', '#'+str(forum_note.number)),
        action=action
    )

    if not EMAIL_PROGRAM_CHAIRS:
        committee.remove(PROGRAM_CHAIRS_ID)
    client.post_message(email_subject, committee, email_body)
