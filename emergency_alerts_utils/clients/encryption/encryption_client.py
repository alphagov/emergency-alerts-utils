from itsdangerous import URLSafeSerializer


class Encryption:
    def init_app(self, app):
        self.serializer = URLSafeSerializer(app.config.get("ENCRYPTION_SECRET_KEY"))
        self.salt = app.config.get("ENCRYPTION_DANGEROUS_SALT")

    def encrypt(self, thing_to_encrypt):
        return self.serializer.dumps(thing_to_encrypt, salt=self.salt)

    def decrypt(self, thing_to_decrypt):
        return self.serializer.loads(thing_to_decrypt, salt=self.salt)
