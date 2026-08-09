from .database import get_connection


def get_top_senders(limit=50):
    """Return senders ordered by message count."""

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            sender_email,
            COUNT(*) AS message_count,
            MIN(date) AS oldest_message,
            MAX(date) AS newest_message
        FROM messages
        WHERE sender_email != ''
        GROUP BY sender_email
        ORDER BY message_count DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    connection.close()

    return rows
