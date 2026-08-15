from datetime import datetime, timezone


class CollectorProcessor:
    """
    Processes data produced by monitoring collectors.

    Collectors are responsible for gathering current system data.
    This class handles timestamps, processing, and optional storage.
    """

    def __init__(self, database=None):
        self.database = database

    def process(self, data):
        """
        Process a collector result and add a UTC timestamp.
        """

        if not isinstance(data, dict):
            raise TypeError("Collector data must be a dictionary.")

        processed = dict(data)

        processed["timestamp"] = datetime.now(
            timezone.utc
        ).isoformat()

        return processed

    def save(self, data):
        """
        Save processed collector data to the database.

        Database integration will be implemented separately.
        """

        if self.database is None:
            return False

        if not hasattr(self.database, "save_collector_data"):
            raise AttributeError(
                "Database does not support save_collector_data()."
            )

        self.database.save_collector_data(data)

        return True

    def process_and_save(self, data, save=False):
        """
        Process collector data and optionally save it.
        """

        processed = self.process(data)

        if save:
            self.save(processed)

        return processed
