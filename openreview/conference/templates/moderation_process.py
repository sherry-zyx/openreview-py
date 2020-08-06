def process(client, note, invitation):
    from datetime import datetime
    CONFERENCE_ID = ''
    PROGRAM_CHAIRS_ID = ''

    comment_note = client.get_note(note.referent)

    spam_comment_invitation_id = CONFERENCE_ID+'/-/Spam_Public_Comment'

    comment_note.readers = [PROGRAM_CHAIRS_ID, comment_note.signatures[0]]
    comment_note.writers = [PROGRAM_CHAIRS_ID]
    comment_note.signatures = [PROGRAM_CHAIRS_ID]
    comment_note.invitation = spam_comment_invitation_id

    client.post_note(comment_note)
