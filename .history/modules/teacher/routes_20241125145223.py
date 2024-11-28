@teacher_bp.route('/start_session', methods=['POST'])
@login_required
def start_session():
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized access'}), 403

    # Fetch batch_id and course_id from request JSON
    batch_id = request.json.get('batch_id')
    course_code = request.json.get('course_code')  # Use course_code instead of course_id for clarity

    if not batch_id or not course_code:
        return jsonify({'error': 'Batch ID and Course Code are required'}), 400

    # Verify if the course exists
    course = Course.query.filter_by(code=course_code).first()
    if not course:
        return jsonify({'error': 'Invalid course'}), 400

    # Fetch students enrolled in the course and batch
    enrolled_students = Student.query.join(StudentCourse, Student.roll_number == StudentCourse.roll_number).filter(
        StudentCourse.course_code == course.code,
        Student.batch == batch_id
    ).all()

    if not enrolled_students:
        return jsonify({'error': 'No students found for this batch and course'}), 400

    # End expired sessions
    end_expired_sessions()

    # Create a new session
    session_id = str(uuid.uuid4())
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=30)  # Session duration is 30 minutes

    new_session = AttendanceSession(
        session_id=session_id,
        teacher_id=current_user.id,
        batch_id=batch_id,
        course_id=course_code,
        start_time=start_time,
        end_time=end_time,
        active=True
    )
    db.session.add(new_session)
    db.session.commit()

    return jsonify({
        'message': 'Session started successfully',
        'session': {
            'session_id': session_id,
            'batch_id': batch_id,
            'course_code': course_code,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
    })


@teacher_bp.route('/save_attendance', methods=['POST'])
@login_required
def save_attendance():
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized access'}), 403

    # Get attendance data from request
    attendance_data = request.json.get('attendance', [])
    if not attendance_data:
        return jsonify({'error': 'No attendance data provided'}), 400

    for record in attendance_data:
        roll_number = record.get('roll_number')
        session_id = record.get('session_id')
        status = record.get('status')

        # Validate record fields
        if not roll_number or not session_id or not status:
            return jsonify({'error': 'Incomplete attendance record'}), 400

        # Fetch the student and session
        student = Student.query.filter_by(roll_number=roll_number).first()
        session = AttendanceSession.query.filter_by(session_id=session_id, active=True).first()

        if not student or not session:
            continue  # Skip invalid records

        # Record attendance
        attendance = Attendance(
            session_id=session.id,
            student_id=student.id,
            name=student.name,
            roll_number=student.roll_number,
            batch_id=student.batch,
            status=status,
            timestamp=datetime.now()
        )
        db.session.add(attendance)

    db.session.commit()
    return jsonify({'message': 'Attendance saved successfully'})


@teacher_bp.route('/fetch_students', methods=['GET'])
@login_required
def fetch_students():
    batch_id = request.args.get('batch_id')
    course_code = request.args.get('course_code')

    if not batch_id or not course_code:
        return jsonify({'error': 'Batch ID and Course Code are required'}), 400

    # Fetch students enrolled in the course and batch
    students = Student.query.join(StudentCourse, Student.roll_number == StudentCourse.roll_number).filter(
        StudentCourse.course_code == course_code,
        Student.batch == batch_id
    ).all()

    if not students:
        return jsonify({'error': 'No students found for this batch and course'}), 400

    # Prepare student data
    student_list = [{'name': student.name, 'roll_number': student.roll_number, 'attendance_status': 'Absent'} for student in students]
    return jsonify(student_list)
