class DatawargaError(Exception):
    """Base exception for all domain errors."""

    pass


class NotFoundError(DatawargaError):
    def __init__(self, resource: str, identifier: str) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} '{identifier}' not found")


class ValidationError(DatawargaError):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PaymentAlreadyExistsError(DatawargaError):
    def __init__(self, periode_bulan: str, periode_tahun: str) -> None:
        self.periode_bulan = periode_bulan
        self.periode_tahun = periode_tahun
        super().__init__(
            f"Pembayaran untuk periode {periode_bulan}/{periode_tahun} sudah ada"
        )
