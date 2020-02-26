class ERMError(Exception):
    pass

class DBError(ERMError):
    pass

class NoDataError(ERMError):
    def __init__(self, data_name):
        self.data_name = data_name

class MessagingError(ERMError):
    def __init__(self, error_data):
        self.error_data = error_data
