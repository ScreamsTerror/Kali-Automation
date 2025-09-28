import os

ETTER_DNS_PATH = "/usr/share/ettercap/etter.dns"

def add_spoof_entry(domain, ip):
    entry = f"{domain} A {ip}\n"
    try:
        with open(ETTER_DNS_PATH, "a") as f:
            f.write(entry)
        print(f"✅ Added spoof: {domain} → {ip}")
    except PermissionError:
        print("❌ Permission denied. Try running with sudo.")
    except Exception as e:
        print("❌ Error:", e)

def main():
    print("🧪 Ettercap DNS Spoof Entry Tool")
    while True:
        domain = input("Enter domain to spoof (or 'done' to exit): ").strip()
        if domain.lower() == "done":
            break
        ip = input(f"Enter fake IP for {domain}: ").strip()
        add_spoof_entry(domain, ip)

if __name__ == "__main__":
    main()