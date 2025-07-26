from src.notifications import EmailSenderInterface


class StubEmailSender(EmailSenderInterface):

    async def send_activation_email(self, email: str, activation_link: str) -> None:
        """
        Stub implementation for sending an activation email.

        Args:
            email (str): The recipient's email address.
            activation_link (str): The activation link to include in the email.
        """
        return None

    async def send_activation_complete_email(self, email: str, login_link: str) -> None:
        """
        Stub implementation for sending an account activation complete email.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        return None

    async def send_password_reset_email(self, email: str, reset_link: str) -> None:
        """
        Stub implementation for sending a password reset email.

        Args:
            email (str): The recipient's email address.
            reset_link (str): The password reset link to include in the email.
        """
        return None

    async def send_password_reset_complete_email(
        self, email: str, login_link: str
    ) -> None:
        """
        Stub implementation for sending a password reset complete email.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        return None
