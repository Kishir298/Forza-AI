from memory.database import get_connection


class MemoryManager:


    def save_memory(self, category, information, importance=5):

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
                importance
            )
        )

        connection.commit()
        connection.close()



    def get_memories(self):

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
