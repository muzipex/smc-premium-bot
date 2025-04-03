import tkinter as tk
from tkinter import ttk, messagebox

class MT5LoginWindow:
    def __init__(self):
        self.login_info = None
        self.window = tk.Tk()
        self.window.title("MT5 Login")
        self.window.geometry("300x200")
        self.window.resizable(False, False)
        
        # Center window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

        # Create main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Login ID
        ttk.Label(main_frame, text="Login ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.login_var = tk.StringVar()
        self.login_entry = ttk.Entry(main_frame, textvariable=self.login_var)
        self.login_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        # Password
        ttk.Label(main_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(main_frame, textvariable=self.password_var, show="*")
        self.password_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)

        # Server
        ttk.Label(main_frame, text="Server:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.server_var = tk.StringVar()
        self.server_entry = ttk.Entry(main_frame, textvariable=self.server_var)
        self.server_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)

        # Login button
        login_button = ttk.Button(main_frame, text="Login", command=self.validate_and_login)
        login_button.grid(row=3, column=0, columnspan=2, pady=20)

        # Set default values
        self.login_var.set("208704579")
        self.server_var.set("Exness-MT5Trial9")

    def validate_and_login(self):
        login = self.login_var.get().strip()
        password = self.password_var.get().strip()
        server = self.server_var.get().strip()

        if not all([login, password, server]):
            messagebox.showerror("Error", "All fields are required!")
            return

        try:
            login_id = int(login)
            self.login_info = {
                'login': login_id,
                'password': password,
                'server': server
            }
            self.window.destroy()  # Close window immediately after successful login
        except ValueError:
            messagebox.showerror("Error", "Login ID must be a number!")

    def get_login_info(self):
        self.window.mainloop()
        return self.login_info  # Return login info after window is closed
