from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.security import set_password
from developer.models import Developer
from teacher.models import Teacher
from student.models import Student
from attendance.models import AttendanceSession, AttendanceRecord


class Command(BaseCommand):
    help = "Seed rich multi-class data for FaceMate including students, teachers, and attendance records."

    def handle(self, *args, **options):
        self.stdout.write("Seeding FaceMate multi-class demo data...")

        # 1. Teachers with multi-class assignments
        teachers_data = [
            {
                "name": "Rajesh Kumar",
                "email": "rajesh.kumar@facemate.com",
                "class_teacher_for": "10-A, 10-B",
                "courses": "Mathematics, Physics",
            },
            {
                "name": "Priya Sharma",
                "email": "priya.sharma@facemate.com",
                "class_teacher_for": "9-A, 9-B",
                "courses": "English, Social Studies",
            },
            {
                "name": "Amit Patel",
                "email": "amit.patel@facemate.com",
                "class_teacher_for": "11-A, 11-B, 12-A",
                "courses": "Chemistry, Computer Science",
            },
            {
                "name": "Demo Teacher",
                "email": "demo.teacher@facemate.local",
                "class_teacher_for": "All",
                "courses": "All School Subjects",
            },
        ]

        for t_info in teachers_data:
            teacher, _ = Teacher.objects.get_or_create(
                email=t_info["email"],
                defaults={
                    "name": t_info["name"],
                    "class_teacher_for": t_info["class_teacher_for"],
                    "courses": t_info["courses"],
                },
            )
            teacher.name = t_info["name"]
            teacher.class_teacher_for = t_info["class_teacher_for"]
            teacher.courses = t_info["courses"]
            set_password(teacher, "teacher123")
            teacher.save()
            self.stdout.write(f"  Teacher: {teacher.name} -> {teacher.class_teacher_for}")

        # 2. Students across 7 classes
        students_data = [
            # Class 9-A
            {"name": "Rohan Gupta", "email": "rohan.gupta@student.facemate.com", "roll_number": "901", "enrollment_number": "EN0901", "class_name": "9", "section": "A"},
            {"name": "Sneha Reddy", "email": "sneha.reddy@student.facemate.com", "roll_number": "902", "enrollment_number": "EN0902", "class_name": "9", "section": "A"},
            {"name": "Vikram Singh", "email": "vikram.singh@student.facemate.com", "roll_number": "903", "enrollment_number": "EN0903", "class_name": "9", "section": "A"},
            {"name": "Tanvi Joshi", "email": "tanvi.joshi@student.facemate.com", "roll_number": "904", "enrollment_number": "EN0904", "class_name": "9", "section": "A"},

            # Class 9-B
            {"name": "Ananya Iyer", "email": "ananya.iyer@student.facemate.com", "roll_number": "905", "enrollment_number": "EN2024004", "class_name": "9", "section": "B"},
            {"name": "Kabir Malhotra", "email": "kabir.malhotra@student.facemate.com", "roll_number": "906", "enrollment_number": "EN0906", "class_name": "9", "section": "B"},
            {"name": "Meera Nair", "email": "meera.nair@student.facemate.com", "roll_number": "907", "enrollment_number": "EN0907", "class_name": "9", "section": "B"},
            {"name": "Aryan Deshmukh", "email": "aryan.deshmukh@student.facemate.com", "roll_number": "908", "enrollment_number": "EN0908", "class_name": "9", "section": "B"},

            # Class 10-A
            {"name": "Aarav Verma", "email": "aarav.verma@student.facemate.com", "roll_number": "1001", "enrollment_number": "EN2024001", "class_name": "10", "section": "A"},
            {"name": "Diya Mehta", "email": "diya.mehta@student.facemate.com", "roll_number": "1002", "enrollment_number": "EN2024002", "class_name": "10", "section": "A"},
            {"name": "Siddharth Rao", "email": "siddharth.rao@student.facemate.com", "roll_number": "1003", "enrollment_number": "EN1003", "class_name": "10", "section": "A"},
            {"name": "Riya Sen", "email": "riya.sen@student.facemate.com", "roll_number": "1004", "enrollment_number": "EN1004", "class_name": "10", "section": "A"},

            # Class 10-B
            {"name": "Aditya Chopra", "email": "aditya.chopra@student.facemate.com", "roll_number": "1005", "enrollment_number": "EN1005", "class_name": "10", "section": "B"},
            {"name": "Ishita Kapoor", "email": "ishita.kapoor@student.facemate.com", "roll_number": "1006", "enrollment_number": "EN1006", "class_name": "10", "section": "B"},
            {"name": "Varun Dhawan", "email": "varun.dhawan@student.facemate.com", "roll_number": "1007", "enrollment_number": "EN1007", "class_name": "10", "section": "B"},
            {"name": "Pooja Hegde", "email": "pooja.hegde@student.facemate.com", "roll_number": "1008", "enrollment_number": "EN1008", "class_name": "10", "section": "B"},

            # Class 11-A
            {"name": "Kunal Roy", "email": "kunal.roy@student.facemate.com", "roll_number": "1101", "enrollment_number": "EN1101", "class_name": "11", "section": "A"},
            {"name": "Natasha DSouza", "email": "natasha.dsouza@student.facemate.com", "roll_number": "1102", "enrollment_number": "EN1102", "class_name": "11", "section": "A"},
            {"name": "Harshit Bansal", "email": "harshit.bansal@student.facemate.com", "roll_number": "1103", "enrollment_number": "EN1103", "class_name": "11", "section": "A"},
            {"name": "Simran Kaur", "email": "simran.kaur@student.facemate.com", "roll_number": "1104", "enrollment_number": "EN1104", "class_name": "11", "section": "A"},

            # Class 11-B
            {"name": "Dev Patel", "email": "dev.patel@student.facemate.com", "roll_number": "1105", "enrollment_number": "EN1105", "class_name": "11", "section": "B"},
            {"name": "Alia Bhatt", "email": "alia.bhatt@student.facemate.com", "roll_number": "1106", "enrollment_number": "EN1106", "class_name": "11", "section": "B"},
            {"name": "Rahul Dravid", "email": "rahul.dravid@student.facemate.com", "roll_number": "1107", "enrollment_number": "EN1107", "class_name": "11", "section": "B"},
            {"name": "Sanya Mirza", "email": "sanya.mirza@student.facemate.com", "roll_number": "1108", "enrollment_number": "EN1108", "class_name": "11", "section": "B"},

            # Class 12-A
            {"name": "Manav Sharma", "email": "manav.sharma@student.facemate.com", "roll_number": "1201", "enrollment_number": "EN1201", "class_name": "12", "section": "A"},
            {"name": "Kriti Sanon", "email": "kriti.sanon@student.facemate.com", "roll_number": "1202", "enrollment_number": "EN1202", "class_name": "12", "section": "A"},
            {"name": "Yash Vardhan", "email": "yash.vardhan@student.facemate.com", "roll_number": "1203", "enrollment_number": "EN1203", "class_name": "12", "section": "A"},
            {"name": "Neha Kakkar", "email": "neha.kakkar@student.facemate.com", "roll_number": "1204", "enrollment_number": "EN1204", "class_name": "12", "section": "A"},
        ]

        created_students = []
        for s_info in students_data:
            student = Student.objects.filter(email=s_info["email"]).first()
            if not student:
                student = Student.objects.filter(enrollment_number=s_info["enrollment_number"]).first()
            if not student:
                student = Student.objects.create(**s_info)
            else:
                for k, v in s_info.items():
                    setattr(student, k, v)
            set_password(student, "student123")
            student.save()
            created_students.append(student)

        self.stdout.write(f"  Created/Updated {len(created_students)} students across 7 classes.")

        # 3. Attendance Sessions and Records for the past 5 days
        today = timezone.localdate()
        classes_sections = [
            ("9", "A", "priya.sharma@facemate.com"),
            ("9", "B", "priya.sharma@facemate.com"),
            ("10", "A", "rajesh.kumar@facemate.com"),
            ("10", "B", "rajesh.kumar@facemate.com"),
            ("11", "A", "amit.patel@facemate.com"),
            ("11", "B", "amit.patel@facemate.com"),
            ("12", "A", "amit.patel@facemate.com"),
        ]

        total_sessions = 0
        total_records = 0

        for day_offset in range(5):
            s_date = today - timedelta(days=day_offset)
            if s_date.weekday() == 6:  # Skip Sundays
                continue

            for class_name, section, teacher_email in classes_sections:
                teacher = Teacher.objects.get(email=teacher_email)
                session, _ = AttendanceSession.objects.get_or_create(
                    teacher=teacher,
                    class_name=class_name,
                    section=section,
                    session_date=s_date,
                )
                total_sessions += 1

                class_students = Student.objects.filter(class_name=class_name, section=section)
                for idx, student in enumerate(class_students):
                    status = "Absent" if (idx + day_offset) % 4 == 3 else "Present"
                    AttendanceRecord.objects.update_or_create(
                        session=session,
                        student=student,
                        defaults={"status": status},
                    )
                    total_records += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded demo data: {len(teachers_data)} teachers, {len(created_students)} students, {total_sessions} sessions, and {total_records} attendance records."
        ))
