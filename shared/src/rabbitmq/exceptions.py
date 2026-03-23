class RetryableProcessingError(Exception):
    pass


class NonRetryableProcessingError(Exception):
    pass