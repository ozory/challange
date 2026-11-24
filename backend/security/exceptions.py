class SecurityViolation(Exception):
    """Entrada bloqueada por uma regra de segurança. `public_message` é seguro para o cliente."""

    def __init__(self, code: str, public_message: str = "Entrada bloqueada por política de segurança"):
        super().__init__(code)
        self.code = code
        self.public_message = public_message
