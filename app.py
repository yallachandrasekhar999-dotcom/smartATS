import os
import io
import json
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

from config import Config
from models import db, User, Resume, Skill, JobDescription, ATSReport, JobPosting
from parser import parse_resume, parse_job_description
from recommender import calculate_ats_score, analyze_resume_suggestions, recommend_jobs, generate_alignment_advice

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database and security
db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Setup upload folder check on startup
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# ----------------------------------------------------
# Core Views & Authentication Routes
# ----------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")
            
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        # Validation checks
        if User.query.filter_by(email=email).first():
            flash("Email address already registered.", "danger")
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return redirect(url_for('register'))
            
        hashed_pass = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_pass,
            role=role
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash("Account created successfully! Welcome to SmartATS.", "success")
        return redirect(url_for('dashboard'))
        
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have logged out successfully.", "success")
    return redirect(url_for('index'))


# ----------------------------------------------------
# Candidate Dashboard & Resume Actions
# ----------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    # Load user resumes
    resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).all()
    
    total_resumes = len(resumes)
    
    # Calculate best and average scores
    reports = ATSReport.query.filter_by(user_id=current_user.id).all()
    scores = [rep.score for rep in reports]
    
    best_score = round(max(scores), 1) if scores else 0
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    
    # Track skill count across all resumes
    all_skills = set()
    skill_dist = {}
    for res in resumes:
        for sk in res.skills:
            all_skills.add(sk)
            
    # Resolve skill categories distribution count
    for skill_name in all_skills:
        skill_obj = Skill.query.filter_by(name=skill_name).first()
        if skill_obj:
            cat = skill_obj.category
            skill_dist[cat] = skill_dist.get(cat, 0) + 1
            
    # Resolve score trend logs for lines graph (last 7 analyses)
    trend_reports = ATSReport.query.filter_by(user_id=current_user.id).order_by(ATSReport.created_at.asc()).all()
    trend_data = []
    for r in trend_reports[-7:]:
        date_str = r.created_at.strftime('%b %d')
        trend_data.append({'date': date_str, 'score': r.score})
        
    return render_template('dashboard.html', 
                           resumes=resumes,
                           total_resumes=total_resumes,
                           best_score=best_score,
                           avg_score=avg_score,
                           total_skills=len(all_skills),
                           skill_dist=skill_dist,
                           trend_data=trend_data)


@app.route('/analyze', methods=['GET', 'POST'])
@login_required
def analyze_resume_route():
    report = None
    resume = None
    
    # Fetch sample job descriptions for dropdown autofill
    sample_jobs = JobPosting.query.all()
    # Fetch user's existing resumes for dropdown select
    select_resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.version.desc()).all()
    
    # If request is GET and a specific resume ID is requested, fetch and render result of its top score report
    req_resume_id = request.args.get('resume_id')
    if request.method == 'GET' and req_resume_id:
        resume = Resume.query.filter_by(id=req_resume_id, user_id=current_user.id).first()
        if resume and resume.reports:
            # Sort reports by score descending
            sorted_reports = sorted(resume.reports, key=lambda x: x.score, reverse=True)
            report = sorted_reports[0]
            alignment_advice = generate_alignment_advice(
                report.matched_skills,
                report.missing_skills,
                report.suggestions.get('weak_sections', [])
            )
            return render_template('analyze.html', report=report, resume=resume, sample_jobs=sample_jobs, select_resumes=select_resumes, alignment_advice=alignment_advice)
    if request.method == 'POST':
        jd_text = request.form.get('job_description')
        existing_id = request.form.get('existing_resume_id')
        track_version = request.form.get('track_version') == 'on'
        
        parsed_data = None
        
        if existing_id:
            # Match against existing parsed resume
            resume = Resume.query.filter_by(id=existing_id, user_id=current_user.id).first()
            if not resume:
                flash("Selected resume not found.", "danger")
                return redirect(url_for('analyze_resume_route'))
            # Format parsing structure from DB properties
            parsed_data = {
                'name': resume.parsed_name,
                'email': resume.parsed_email,
                'phone': resume.parsed_phone,
                'skills': resume.skills,
                'education': resume.education,
                'experience': resume.experience,
                'certifications': resume.certifications,
                'raw_text': parse_resume(resume.filepath).get('raw_text', '') if os.path.exists(resume.filepath) else ''
            }
        else:
            # Parse a newly uploaded resume
            file = request.files.get('resume_file')
            if not file or file.filename == '':
                flash("Please upload a file or select a past resume upload.", "danger")
                return redirect(url_for('analyze_resume_route'))
                
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Resolve version increments if matching file name exists
            version = 1
            if track_version:
                existing_matches = Resume.query.filter_by(user_id=current_user.id, filename=filename).all()
                if existing_matches:
                    max_ver = max([r.version for r in existing_matches])
                    version = max_ver + 1
                    # Append suffix to filesystem save path to prevent overwriting
                    base, ext = os.path.splitext(filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{base}_v{version}{ext}")
            
            file.save(filepath)
            
            # Extract content from resume using spaCy parser
            parsed_data = parse_resume(filepath)
            if not parsed_data:
                flash("Failed to parse resume document content. Verify formatting.", "danger")
                return redirect(url_for('analyze_resume_route'))
                
            # Create Resume db model record
            resume = Resume(
                user_id=current_user.id,
                filename=filename,
                filepath=filepath,
                version=version,
                parsed_name=parsed_data['name'],
                parsed_email=parsed_data['email'],
                parsed_phone=parsed_data['phone']
            )
            resume.skills = parsed_data['skills']
            resume.education = parsed_data['education']
            resume.experience = parsed_data['experience']
            resume.certifications = parsed_data['certifications']
            
            db.session.add(resume)
            db.session.commit()
            
        # Parse Job Description
        jd_data = parse_job_description(jd_text)
        
        # Calculate ATS score match
        score_result = calculate_ats_score(parsed_data, jd_data)
        
        # Generate suggestions
        suggestions_data = analyze_resume_suggestions(parsed_data)
        # Inject detailed scoring breakdown for charts
        suggestions_data['breakdown'] = score_result['breakdown']
        
        # Create JobDescription DB entry
        jd_obj = JobDescription(
            title="Matched Target Profile",
            raw_text=jd_text,
            extracted_skills=jd_data['skills']
        )
        db.session.add(jd_obj)
        db.session.commit()
        
        # Create ATS Report
        report = ATSReport(
            user_id=current_user.id,
            resume_id=resume.id,
            job_description_id=jd_obj.id,
            score=score_result['score'],
            category=score_result['category'],
            matched_skills=score_result['matched_skills'],
            missing_skills=score_result['missing_skills'],
            suggestions=suggestions_data
        )
        
        db.session.add(report)
        db.session.commit()
        
        flash("ATS Score prediction completed successfully!", "success")
        
    alignment_advice = None
    if report:
        alignment_advice = generate_alignment_advice(
            report.matched_skills,
            report.missing_skills,
            report.suggestions.get('weak_sections', [])
        )
        
    return render_template('analyze.html', report=report, resume=resume, sample_jobs=sample_jobs, select_resumes=select_resumes, alignment_advice=alignment_advice)


@app.route('/resume/delete/<int:id>')
@login_required
def delete_resume(id):
    resume = Resume.query.filter_by(id=id, user_id=current_user.id).first()
    if not resume:
        flash("Resume record not found.", "danger")
        return redirect(url_for('dashboard'))
        
    # Delete uploaded physical file if present
    if os.path.exists(resume.filepath):
        try:
            os.remove(resume.filepath)
        except Exception as e:
            print(f"Failed to delete resume file: {e}")
            
    db.session.delete(resume)
    db.session.commit()
    flash("Resume and all matching analysis reports deleted.", "success")
    return redirect(url_for('dashboard'))


# ----------------------------------------------------
# Recruiter Multi-Candidate Portal
# ----------------------------------------------------

@app.route('/recruiter', methods=['GET', 'POST'])
@login_required
def recruiter_dashboard_route():
    candidates = []
    sample_jobs = JobPosting.query.all()
    
    if request.method == 'POST':
        files = request.files.getlist('resumes')
        jd_text = request.form.get('job_description')
        
        if not files or files[0].filename == '':
            flash("Please select at least one resume document to rank.", "danger")
            return redirect(url_for('recruiter_dashboard_route'))
            
        # Parse JD
        jd_data = parse_job_description(jd_text)
        jd_obj = JobDescription(
            title="Recruiter Ranking Position",
            raw_text=jd_text,
            extracted_skills=jd_data['skills']
        )
        db.session.add(jd_obj)
        db.session.commit()
        
        for file in files:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"recruiter_{current_user.id}_{filename}")
            file.save(filepath)
            
            # Parse Candidate Details
            parsed_data = parse_resume(filepath)
            if not parsed_data:
                # Cleanup and skip corrupted
                if os.path.exists(filepath): os.remove(filepath)
                continue
                
            # Create a Resume Entry in DB for recruiter record keeping
            res_obj = Resume(
                user_id=current_user.id,
                filename=filename,
                filepath=filepath,
                version=1,
                parsed_name=parsed_data['name'],
                parsed_email=parsed_data['email'],
                parsed_phone=parsed_data['phone']
            )
            res_obj.skills = parsed_data['skills']
            res_obj.education = parsed_data['education']
            res_obj.experience = parsed_data['experience']
            res_obj.certifications = parsed_data['certifications']
            
            db.session.add(res_obj)
            db.session.commit()
            
            # Evaluate match score against target position
            match_res = calculate_ats_score(parsed_data, jd_data)
            suggestions_data = analyze_resume_suggestions(parsed_data)
            suggestions_data['breakdown'] = match_res['breakdown']
            
            # Save matching report
            report_obj = ATSReport(
                user_id=current_user.id,
                resume_id=res_obj.id,
                job_description_id=jd_obj.id,
                score=match_res['score'],
                category=match_res['category'],
                matched_skills=match_res['matched_skills'],
                missing_skills=match_res['missing_skills'],
                suggestions=suggestions_data
            )
            db.session.add(report_obj)
            db.session.commit()
            
            candidates.append({
                'name': parsed_data['name'],
                'filename': filename,
                'score': match_res['score'],
                'matched_skills': match_res['matched_skills'],
                'missing_skills': match_res['missing_skills'],
                'resume_id': res_obj.id,
                'report_id': report_obj.id
            })
            
        # Rank descending based on score
        candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
        flash(f"Ranked {len(candidates)} candidates against job description requirements!", "success")
        
    return render_template('recruiter.html', candidates=candidates, sample_jobs=sample_jobs)


# ----------------------------------------------------
# Job Recommendations view
# ----------------------------------------------------

@app.route('/jobs')
@login_required
def job_recommendations_route():
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()
    has_resume = latest_resume is not None
    
    recommendations = []
    if has_resume:
        job_postings = JobPosting.query.all()
        # Query match engine
        recommendations = recommend_jobs(latest_resume.skills, job_postings)
        
    return render_template('job_recommendations.html', 
                           has_resume=has_resume, 
                           recommendations=recommendations)


# ----------------------------------------------------
# User Settings & Profiles
# ----------------------------------------------------

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        password = request.form.get('password')
        
        # Check email uniqueness
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != current_user.id:
            flash("Email address already in use.", "danger")
            return redirect(url_for('profile'))
            
        # Check username uniqueness
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != current_user.id:
            flash("Username already in use.", "danger")
            return redirect(url_for('profile'))
            
        current_user.username = username
        current_user.email = email
        current_user.role = role
        
        if password:
            current_user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))
        
    return render_template('profile.html')


# ----------------------------------------------------
# Administrator Dashboards & Exclusive Auth
# ----------------------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if not user or user.role != 'admin':
            flash("You are not Authorized to this", "danger")
            return redirect(url_for('admin_login'))
            
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Welcome to the Admin Console!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid password. Please try again.", "danger")
            return redirect(url_for('admin_login'))
            
    return render_template('admin_login.html')


@app.route('/admin')
def admin_dashboard():
    if not current_user.is_authenticated or current_user.role != 'admin':
        return redirect(url_for('admin_login'))
        
    total_users = User.query.count()
    total_resumes = Resume.query.count()
    total_reports = ATSReport.query.count()
    users_list = User.query.order_by(User.created_at.desc()).all()
    
    return render_template('admin.html', 
                           total_users=total_users, 
                           total_resumes=total_resumes, 
                           total_reports=total_reports, 
                           users_list=users_list)


@app.route('/admin/action/<string:action_type>', methods=['POST'])
def admin_action(action_type):
    if not current_user.is_authenticated or current_user.role != 'admin':
        return redirect(url_for('admin_login'))
        
    if action_type == 'seed_db':
        from seed import seed_database
        # Re-run Database initialization
        seed_database()
        logout_user()
        flash("Database cleared and seeded. Please login using admin123.", "success")
        return redirect(url_for('admin_login'))
        
    elif action_type == 'clear_resumes':
        # Remove physical files
        resumes = Resume.query.all()
        for res in resumes:
            if os.path.exists(res.filepath):
                try: os.remove(res.filepath)
                except: pass
        Resume.query.delete()
        ATSReport.query.delete()
        db.session.commit()
        flash("All resumes and dependent match reports purged.", "success")
        
    elif action_type == 'clear_reports':
        ATSReport.query.delete()
        db.session.commit()
        flash("All match reports cleared.", "success")
        
    return redirect(url_for('admin_dashboard'))


# ----------------------------------------------------
# Downloadable ReportLab PDF Generator
# ----------------------------------------------------

@app.route('/report/<int:report_id>/pdf')
@login_required
def download_pdf_report(report_id):
    report = ATSReport.query.filter_by(id=report_id).first()
    if not report:
        flash("Report not found.", "danger")
        return redirect(url_for('dashboard'))
        
    if report.user_id != current_user.id and current_user.role != 'admin' and current_user.role != 'recruiter':
        flash("Unauthorized to access this report.", "danger")
        return redirect(url_for('dashboard'))
        
    # Set up ReportLab Document in Memory buffer
    buffer = io.BytesIO()
    doc = io.BytesIO()
    
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    
    # Configure PDF settings
    pdf_doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []
    
    # Standard styles setup
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#4f46e5'),
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4b5563'),
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'HeadingSec',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#374151'),
        spaceAfter=6
    )
    
    code_style = ParagraphStyle(
        'CodeStyleCustom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#b91c1c'),
        spaceAfter=6
    )
    
    # PDF Title & Header details
    story.append(Paragraph("SmartATS Resume Evaluation Report", title_style))
    story.append(Paragraph(f"Generated on {report.created_at.strftime('%Y-%b-%d %H:%M')} for Candidate: {report.resume.parsed_name or 'N/A'}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Table layout for key metrics
    meta_data = [
        [Paragraph("<b>ATS Score:</b>", body_style), Paragraph(f"<b>{report.score}%</b> ({report.category} Fit)", body_style),
         Paragraph("<b>Resume File:</b>", body_style), Paragraph(report.resume.filename, body_style)],
        [Paragraph("<b>Email:</b>", body_style), Paragraph(report.resume.parsed_email or 'Not Found', body_style),
         Paragraph("<b>Phone:</b>", body_style), Paragraph(report.resume.parsed_phone or 'Not Found', body_style)]
    ]
    t = Table(meta_data, colWidths=[80, 170, 80, 170])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f3f4f6')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    # Matching breakdown Section
    story.append(Paragraph("ATS Scoring Breakdown Points", heading_style))
    pts = report.suggestions.get('breakdown', {})
    breakdown_data = [
        [Paragraph("<b>Category</b>", body_style), Paragraph("<b>Target Score</b>", body_style), Paragraph("<b>Score Earned</b>", body_style)],
        [Paragraph("Skills Match Weight", body_style), Paragraph("60 pts", body_style), Paragraph(f"{pts.get('skills', 0)} pts", body_style)],
        [Paragraph("General Keyword Overlap", body_style), Paragraph("20 pts", body_style), Paragraph(f"{pts.get('keywords', 0)} pts", body_style)],
        [Paragraph("Section Layout & Structure", body_style), Paragraph("10 pts", body_style), Paragraph(f"{pts.get('structure', 0)} pts", body_style)],
        [Paragraph("Contact & Heuristics Check", body_style), Paragraph("10 pts", body_style), Paragraph(f"{pts.get('contact', 0)} pts", body_style)]
    ]
    t_breakdown = Table(breakdown_data, colWidths=[200, 150, 150])
    t_breakdown.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e5e7eb')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d1d5db')),
    ]))
    story.append(t_breakdown)
    story.append(Spacer(1, 15))

    # Skill Gap analysis
    story.append(Paragraph("Skill Gaps Analysis", heading_style))
    matched_str = ", ".join(report.matched_skills) if report.matched_skills else "None"
    missing_str = ", ".join(report.missing_skills) if report.missing_skills else "None"
    
    story.append(Paragraph(f"<b>Matched Skills ({len(report.matched_skills)}):</b> {matched_str}", body_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"<b>Missing Skills ({len(report.missing_skills)}):</b> <font color='#ef4444'>{missing_str}</font>", body_style))
    story.append(Spacer(1, 15))
    
    # Action verbs replacements
    story.append(Paragraph("AI Action Verb Improvements", heading_style))
    verbs = report.suggestions.get('verb_replacements', [])
    if verbs:
        verb_data = [[Paragraph("<b>Weak Phrasing Detected</b>", body_style), Paragraph("<b>Recommended Replacements</b>", body_style)]]
        for v in verbs:
            verb_data.append([
                Paragraph(v['weak'], code_style),
                Paragraph(v['suggested'], body_style)
            ])
        t_verbs = Table(verb_data, colWidths=[200, 300])
        t_verbs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#fee2e2')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#fca5a5')),
        ]))
        story.append(t_verbs)
    else:
        story.append(Paragraph("No weak phrasing or action verbs flagged. Good work!", body_style))
    story.append(Spacer(1, 15))

    # General Improvements
    story.append(Paragraph("Actionable Improvement Recommendations", heading_style))
    improvements = report.suggestions.get('improvements', [])
    for imp in improvements:
        story.append(Paragraph(f"&bull; {imp}", body_style))
        
    # Suggested Learning paths
    learning = report.suggestions.get('learning_path', [])
    if learning:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Recommended Training Paths to Close Skill Gaps:</b>", body_style))
        story.append(Paragraph(", ".join(learning), body_style))

    # Compile PDF document
    pdf_doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"ATS_Report_{report.id}.pdf",
        mimetype='application/pdf'
    )


# ----------------------------------------------------
# Application entry point setup
# ----------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        # Initialize tables on direct execute
        db.create_all()
    app.run(debug=True, port=5000)
