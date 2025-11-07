import csv, json

password = input("Enter password: ")

wallets = []

with open("warm.csv", "r", newline="") as f:
    for row in csv.DictReader(f):
        from _02_main import decrypt_secret
        try:
            decrypted = decrypt_secret(row["sk"].strip(), password)
        except:
            pass
        print(decrypted)
        wallets.append({"sk":decrypted})

with open("warm.json", "w") as f:
    json.dump(wallets, f, ensure_ascii=False, indent=2)