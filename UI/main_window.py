import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.predictor import TrajectoryEngine
from modules.crud import AcademicCRUD
from modules.ai_advisor import AIAdvisorEngine

class EduTrackDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("EduTrack - Smart Academic Trajectory Predictor")
        self.root.geometry("1000x650")
        self.root.configure(bg="#f4f6f9")

        # Header Title
        title_frame = tk.Frame(self.root, bg="#1e293b", height=60)
        title_frame.pack(fill=tk.X)
        title_lbl = tk.Label(title_frame, text="EduTrack: Academic Performance & Goal Simulator", 
                             fg="white", bg="#1e293b", font=("Segoe UI", 16, "bold"))
        title_lbl.pack(pady=12)

        # Main Layout
        main_container = tk.Frame(self.root, bg="#f4f6f9")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Left Controls Panel
        left_panel = tk.LabelFrame(main_container, text=" Student Lookup & Trajectory Engine ", 
                                   font=("Segoe UI", 11, "bold"), bg="white", padx=10, pady=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, width=350)

        tk.Label(left_panel, text="Student ID:", bg="white", font=("Segoe UI", 10)).pack(anchor="w", pady=(5,0))
        self.student_id_entry = tk.Entry(left_panel, font=("Segoe UI", 11), bd=1, relief="solid")
        self.student_id_entry.insert(0, "20255103311")
        self.student_id_entry.pack(fill=tk.X, pady=5)

        load_btn = tk.Button(left_panel, text="Fetch Academic Profile", bg="#2563eb", fg="white", 
                             font=("Segoe UI", 10, "bold"), relief="flat", command=self.load_student_data)
        load_btn.pack(fill=tk.X, pady=8)

        # Target CGPA Predictor Section
        predict_frame = tk.LabelFrame(left_panel, text=" Target CGPA Back-Calculator ", 
                                      font=("Segoe UI", 10, "bold"), bg="white", padx=8, pady=8)
        predict_frame.pack(fill=tk.X, pady=15)

        tk.Label(predict_frame, text="Target CGPA:", bg="white").grid(row=0, column=0, sticky="w", pady=4)
        self.target_cgpa_entry = tk.Entry(predict_frame, width=10)
        self.target_cgpa_entry.grid(row=0, column=1, pady=4)

        tk.Label(predict_frame, text="Remaining Credits:", bg="white").grid(row=1, column=0, sticky="w", pady=4)
        self.rem_credits_entry = tk.Entry(predict_frame, width=10)
        self.rem_credits_entry.grid(row=1, column=1, pady=4)

        calc_btn = tk.Button(predict_frame, text="Calculate Required GPA", bg="#059669", fg="white", 
                             font=("Segoe UI", 9, "bold"), command=self.run_prediction)
        calc_btn.grid(row=2, column=0, columnspan=2, sticky="we", pady=8)

        self.pred_result_lbl = tk.Label(predict_frame, text="Status: Ready", bg="white", fg="#4b5563", wraplength=280)
        self.pred_result_lbl.grid(row=3, column=0, columnspan=2, pady=4)

        # Right Display & Graph Area
        right_panel = tk.Frame(main_container, bg="#f4f6f9")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Treeview Grade Display
        tree_frame = tk.LabelFrame(right_panel, text=" Completed Course Records ", font=("Segoe UI", 10, "bold"), bg="white")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=("Code", "Title", "Credits", "Sem", "Grade", "GP"), show="headings")
        self.tree.heading("Code", text="Course")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Credits", text="Credit")
        self.tree.heading("Sem", text="Semester")
        self.tree.heading("Grade", text="Grade")
        self.tree.heading("GP", text="GP")
        
        self.tree.column("Code", width=80)
        self.tree.column("Title", width=180)
        self.tree.column("Credits", width=60)
        self.tree.column("Sem", width=70)
        self.tree.column("Grade", width=60)
        self.tree.column("GP", width=60)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def load_student_data(self):
        sid = self.student_id_entry.get().strip()
        records = AcademicCRUD.get_student_enrollments(sid)
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not records:
            messagebox.showinfo("Info", "No enrollment records found for this Student ID.")
            return

        for r in records:
            self.tree.insert("", tk.END, values=(
                r['course_code'], r['course_title'], r['credit_hours'], 
                r['semester_no'], r['letter_grade'], r['grade_point']
            ))

    def run_prediction(self):
        try:
            target = float(self.target_cgpa_entry.get())
            rem_credits = float(self.rem_credits_entry.get())
            
            sid = self.student_id_entry.get().strip()
            records = AcademicCRUD.get_student_enrollments(sid)
            current_cgpa, completed_credits = TrajectoryEngine.calculate_current_cgpa(records)

            req_gpa, status = TrajectoryEngine.calculate_target_required_gpa(
                current_cgpa, completed_credits, target, rem_credits
            )
            self.pred_result_lbl.config(text=f"Req. Future GPA: {req_gpa}\nNote: {status}", fg="#1e40af")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric inputs.")