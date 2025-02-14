def process(client, edit, invitation):

    journal = openreview.journal.Journal()

    venue_id = journal.venue_id

    submission = client.get_note(edit.note.forum)

    ## Make the retraction public
    print('Make retraction public')
    invitation = journal.invitation_builder.post_invitation_edit(Invitation(id=journal.get_retraction_release_id(number=submission.number),
            bulk=True,
            invitees=[venue_id],
            readers=['everyone'],
            writers=[venue_id],
            signatures=[venue_id],
            edit={
                'signatures': { 'const': [venue_id ] },
                'readers': { 'const': [ venue_id, journal.get_action_editors_id(number=submission.number), journal.get_authors_id(number=submission.number) ] },
                'writers': { 'const': [ venue_id ] },
                'note': {
                    'id': { 'withInvitation': journal.get_retraction_id(number=submission.number) },
                    'readers': { 'const': [ 'everyone' ] },
                    'nonreaders': { 'const': [] }
                }
            }
    ))

    if edit.note.content['approval']['value'] == 'Yes':
        client.post_note_edit(invitation= journal.get_retracted_id(),
                                signatures=[venue_id],
                                note=openreview.api.Note(id=submission.id,
                                content= {
                                    '_bibtex': {
                                        'value': journal.get_bibtex(submission, journal.retracted_venue_id, anonymous=submission.content['authors'].get('readers', []) != ['everyone'])
                                    }
                                }
        ))

    ## Send email to Authors
    print('Send email to authors')
    client.post_message(
        recipients=[journal.get_authors_id(number=submission.number)],
        subject=f'''[{journal.short_name}] Decision available for retraction request of {journal.short_name} submission {submission.content['title']['value']}''',
        message=f'''Hi {{{{fullname}}}},

As {journal.short_name} Editors-in-Chief, we have submitted our decision on your request to retract your accepted paper at {journal.short_name} titled "{submission.content['title']['value']}".

To view our decision, follow this link: https://openreview.net/forum?id={edit.note.forum}&noteId={edit.note.id}

The {journal.short_name} Editors-in-Chief

''',
        replyTo=journal.contact_info
    )