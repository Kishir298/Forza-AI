from memory.database import (
    get_connection,
    save_collector_data,
    get_collector_history,
)


class MemoryManager:
    """Main interface for Forza's memory system."""

    def save_memory(
        self,
        category,
        information,
        importance=5,
    ):
        """Save a general Forza memory."""

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO memories
            (category, information, importance)
            VALUES (?, ?, ?)
            """,
            (
                category,
                information,
                importance,
            ),
        )

        connection.commit()
        connection.close()

    def get_memories(self):
        """Return general memories ordered by importance."""

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT category, information
            FROM memories
            ORDER BY importance DESC
            """
        )

        results = cursor.fetchall()

        connection.close()

        return results

    def record_collector(self, data):
        """Store processed collector data."""

        save_collector_data(data)

    def get_collector_history(
        self,
        component,
        limit=100,
    ):
        """Return historical readings for a component."""

        return get_collector_history(
            component,
            limit,
        )

    def get_recent_collector(self, component):
        """Return the most recent reading for a component."""

        history = self.get_collector_history(
            component,
            limit=1,
        )

        if not history:
            return None

        return history[0]