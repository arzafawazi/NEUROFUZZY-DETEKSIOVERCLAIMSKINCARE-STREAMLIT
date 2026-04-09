import bcrypt

pw = bcrypt.hashpw("user123".encode(), bcrypt.gensalt())
print(pw.decode())