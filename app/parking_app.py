import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import json
import time
import random
import serial
import serial.tools.list_ports
import qrcode
from PIL import Image, ImageTk
import plate_recognizer
import socket, server


# ---------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------
NUM_SLOTS = 5          # how many parking slots to display
BAUD_RATE = 115200     
FEE_PER_HOUR = 5000    


class ParkingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Parking - Local Dashboard")
        self.root.geometry("720x520")

        # Data queue: the serial-reading thread puts messages here,
        # and the main Tkinter loop takes them out safely.
        self.data_queue = queue.Queue()

        # Holds the current on/off state for each slot (1..NUM_SLOTS)
        self.slot_status = {i: "free" for i in range(1, NUM_SLOTS + 1)}

        # Serial connection object (None until connected)
        self.serial_conn = None
        self.serial_thread = None
        self.serial_running = False

        # Simulation mode flag
        self.simulate_running = False

        self._build_ui()
        # Start Flask server (even without serial) so QR can be accessed from other devices
        import socket, server
        server.start_flask_in_thread(None)
        # Register payment callback immediately (works even without serial)
        server.set_payment_callback(self._payment_completed)

        # Check the queue every 200ms for new slot updates
        self.root.after(200, self._process_queue)
        # Track paid plates
        self.paid_plates = {} # {plate: expiry_time}
        self.root.after(1000, self._update_status_board)

    def _update_status_board(self):
        now = time.time()
        # Remove expired permits
        expired = [p for p, exp in self.paid_plates.items() if exp <= now]
        for p in expired:
            del self.paid_plates[p]
        # Clear treeview
        for item in self.permit_tree.get_children():
            self.permit_tree.delete(item)
        # Populate active permits with HH:MM:SS format
        if self.paid_plates:
            for plate, expiry in self.paid_plates.items():
                remaining = int(expiry - now)
                h = remaining // 3600
                m = (remaining % 3600) // 60
                s = remaining % 60
                time_str = f"{h:02d}:{m:02d}:{s:02d}"
                self.permit_tree.insert("", "end", values=(plate, time_str))
        else:
            self.permit_tree.insert("", "end", values=("No active permits", "-"))
        # schedule next update
        self.root.after(1000, self._update_status_board)

    # -----------------------------------------------------------
    # UI LAYOUT
    # -----------------------------------------------------------
    def _build_ui(self):
        # ---- Top bar: Serial connection controls ----
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="COM Port:").pack(side="left")

        self.port_combo = ttk.Combobox(top_frame, width=15, state="readonly")
        self.port_combo.pack(side="left", padx=5)
        self._refresh_ports()

        ttk.Button(top_frame, text="Refresh Ports", command=self._refresh_ports).pack(side="left", padx=5)
        self.connect_btn = ttk.Button(top_frame, text="Connect", command=self._toggle_serial)
        self.connect_btn.pack(side="left", padx=5)

        self.sim_btn = ttk.Button(top_frame, text="Start Simulation", command=self._toggle_simulation)
        self.sim_btn.pack(side="left", padx=15)

        self.status_label = ttk.Label(top_frame, text="Status: Disconnected", foreground="gray")
        self.status_label.pack(side="right")

        # ---- Middle: Parking slot grid ----
        slots_frame = ttk.LabelFrame(self.root, text="Parking Slots", padding=15)
        slots_frame.pack(fill="x", padx=10, pady=10)

        self.slot_labels = {}
        for i in range(1, NUM_SLOTS + 1):
            lbl = tk.Label(
                slots_frame, text=f"Slot {i}\nFREE",
                width=12, height=4, bg="#4CAF50", fg="white",
                font=("Segoe UI", 10, "bold"), relief="raised"
            )
            lbl.grid(row=0, column=i - 1, padx=8, pady=5)
            self.slot_labels[i] = lbl

        # ---- Bottom: VietQR payment demo section ----
        qr_frame = ttk.LabelFrame(self.root, text="Payment (VietQR demo)", padding=15)
        qr_frame.pack(fill="both", expand=True, padx=10, pady=10)

        controls = ttk.Frame(qr_frame)
        controls.pack(side="left", fill="y", padx=10)

        ttk.Label(controls, text="Parking duration (hours):").pack(anchor="w")
        self.hours_entry = ttk.Entry(controls, width=10)
        self.hours_entry.insert(0, "1")
        self.hours_entry.pack(anchor="w", pady=5)

        ttk.Button(controls, text="Generate QR", command=self._generate_qr).pack(anchor="w", pady=10)
        self.current_plate = ""
        self.plate_label = ttk.Label(controls, text="Plate: -")
        self.plate_label.pack(anchor="w", pady=5)
        ttk.Button(controls, text="Scan Plate", command=self._start_plate_scanner).pack(anchor="w", pady=5)
        ttk.Button(controls, text="Simulate Plate", command=self._simulate_plate).pack(anchor="w", pady=5)
        self.fee_label = ttk.Label(controls, text="Fee: -")
        self.fee_label.pack(anchor="w", pady=5)

        # NOTE: no width/height here on purpose. For a Tkinter Label,
        # width/height mean "characters/lines" while showing text, but
        # silently switch to meaning "pixels" once an image is set.
        # Setting a text-sized width/height here would shrink the label
        # down to a few pixels the moment an image is assigned. We set
        # the pixel size explicitly, later, in _generate_qr() instead.
        # Replace textual permit label with a Treeview table for better view.
        # Create a container frame for the permits table and QR canvas to avoid overlap.
        self.permit_frame = ttk.Frame(qr_frame)
        self.permit_frame.pack(side="right", fill="both", expand=True, padx=10, pady=5)
        # Treeview for active permits (top part)
        self.permit_tree = ttk.Treeview(self.permit_frame, columns=("plate","remaining"), show="headings", height=5)
        self.permit_tree.heading("plate", text="Plate")
        self.permit_tree.heading("remaining", text="Remaining")
        self.permit_tree.column("plate", width=120, anchor="center")
        self.permit_tree.column("remaining", width=120, anchor="center")
        self.permit_tree.pack(fill="x")
        # QR canvas (bottom part)
        self.qr_canvas = tk.Label(self.permit_frame, text="QR code will appear here", relief="sunken")
        self.qr_canvas.pack(side="bottom", fill="both", expand=True, pady=5)


    # -----------------------------------------------------------
    # SERIAL PORT HANDLING
    # -----------------------------------------------------------
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)

    def _toggle_serial(self):
        if self.serial_running:
            self._stop_serial()
        else:
            self._start_serial()

    def _start_serial(self):
        # Start serial connection and launch local Flask server for payment handling
        port = self.port_combo.get()
        if not port:
            messagebox.showwarning("No port selected", "Please select a COM port first.")
            return
        try:
            self.serial_conn = serial.Serial(port, BAUD_RATE, timeout=1)
        except serial.SerialException as e:
            messagebox.showerror("Connection failed", str(e))
            return
        # Register callback with Flask server to update UI after payment
        server.set_payment_callback(self._payment_completed)
        # Provide serial connection to Flask server (already running)
        try:
            server.set_serial_connection(self.serial_conn)
        except Exception as e:
            print('Failed to set serial connection in Flask server:', e)
        self.serial_running = True
        self.serial_thread = threading.Thread(target=self._serial_reader_loop, daemon=True)
        self.serial_thread.start()
        self.connect_btn.config(text="Disconnect")
        self.status_label.config(text=f"Status: Connected to {port}", foreground="green")

    def _stop_serial(self):
        self.serial_running = False
        if self.serial_conn:
            self.serial_conn.close()
            self.serial_conn = None
        self.connect_btn.config(text="Connect")
        self.status_label.config(text="Status: Disconnected", foreground="gray")

    def _serial_reader_loop(self):
        """
        Runs in a background thread. Reads lines from the ESP32 Gateway.
        Expected line format (JSON), one per line, e.g.:
            {"slot_id": 2, "status": "occupied"}
        Adjust the parsing here if your firmware sends a different format
        (for example plain text like "SLOT:2,STATUS:OCCUPIED").
        """
        while self.serial_running and self.serial_conn:
            try:
                line = self.serial_conn.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                data = json.loads(line)
                self.data_queue.put(data)
            except json.JSONDecodeError:
                pass  # ignore malformed/noisy lines
            except serial.SerialException:
                break

    # -----------------------------------------------------------
    # SIMULATION MODE (no hardware needed - great for learning/testing)
    # -----------------------------------------------------------
    def _toggle_simulation(self):
        self.simulate_running = not self.simulate_running
        if self.simulate_running:
            self.sim_btn.config(text="Stop Simulation")
            threading.Thread(target=self._simulation_loop, daemon=True).start()
        else:
            self.sim_btn.config(text="Start Simulation")

    def _simulation_loop(self):
        while self.simulate_running:
            fake_slot = random.randint(1, NUM_SLOTS)
            fake_status = random.choice(["free", "occupied"])
            self.data_queue.put({"slot_id": fake_slot, "status": fake_status})
            time.sleep(2)  # simulate a new event every 2 seconds

    # -----------------------------------------------------------
    # QUEUE PROCESSING -> UPDATE UI (always runs on the main thread)
    # -----------------------------------------------------------
    def _process_queue(self):
        while not self.data_queue.empty():
            data = self.data_queue.get()
            slot_id = data.get("slot_id")
            status = data.get("status")
            if slot_id in self.slot_status:
                self.slot_status[slot_id] = status
                self._update_slot_ui(slot_id, status)
        self.root.after(200, self._process_queue)  # keep checking

    def _update_slot_ui(self, slot_id, status):
        lbl = self.slot_labels[slot_id]
        if status == "occupied":
            lbl.config(bg="#E53935", text=f"Slot {slot_id}\nOCCUPIED")
        else:
            lbl.config(bg="#4CAF50", text=f"Slot {slot_id}\nFREE")

    # -----------------------------------------------------------
    # QR CODE GENERATION (VietQR demo/placeholder)
    # -----------------------------------------------------------
    def _start_plate_scanner(self):
        """Start camera plate recognition (simulated)."""
        def on_plate(plate):
            self.current_plate = plate
            self.plate_label.config(text=f"Plate: {plate}")
        threading.Thread(target=plate_recognizer.start_camera_recognition, args=(on_plate,), daemon=True).start()

    def _generate_qr(self):
        try:
            hours = float(self.hours_entry.get())
        except ValueError:
            messagebox.showwarning("Invalid input", "Please enter a valid number of hours.")
            return
        fee = int(hours * FEE_PER_HOUR)
        self.fee_label.config(text=f"Fee: {fee:,} VND")
        # Determine local IP address reachable from other devices
        try:
            # Use a UDP socket to get the primary network interface IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            # Fallback to hostname resolution
            local_ip = socket.gethostbyname(socket.gethostname())
        # Build URL using reachable IP
        slot_id = 1
        local_url = f"http://{local_ip}:5000/pay/{slot_id}/{fee}"
        img = qrcode.make(local_url)
        img = img.resize((220, 220))
        tk_img = ImageTk.PhotoImage(img)
        self.qr_canvas.config(image=tk_img, text="", width=220, height=220)
        self.qr_canvas.image = tk_img

    def _simulate_plate(self):
        """Simulate a random license plate without using camera."""
        import random
        region = random.choice(["51", "30", "59", "60"])
        letters = random.choice(["A", "B", "C", "D"])
        numbers = random.randint(10000, 99999)
        plate = f"{region}-{letters}{numbers}"
        self.current_plate = plate
        self.plate_label.config(text=f"Plate: {plate}")


    def _payment_completed(self, slot_id, amount):
        """Called from Flask server when user confirms payment."""
        self.root.after(0, lambda: self._process_payment_ui())

    def _process_payment_ui(self):
        print(f'DEBUG: Processing payment UI for plate {self.current_plate}')
        plate = self.current_plate
        hours = float(self.hours_entry.get()) if self.hours_entry.get() else 1
        expiry = time.time() + (hours * 3600)
        if plate:
            self.paid_plates[plate] = expiry
            self._update_status_board()
            # Also send open barrier command to ESP32 (if connected)
            if self.serial_conn:
                try:
                    cmd = {"action": "open_barrier", "plate": plate}
                    self.serial_conn.write((json.dumps(cmd) + "\n").encode())
                except Exception as e:
                    print('Serial write error:', e)


if __name__ == "__main__":
    root = tk.Tk()
    app = ParkingApp(root)
    root.mainloop()
