from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'recruiter', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resumes = db.relationship('Resume', backref='owner', lazy=True, cascade='all, delete-orphan')
    reports = db.relationship('ATSReport', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Resume(db.Model):
    __tablename__ = 'resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    version = db.Column(db.Integer, default=1)
    
    # Parsed Content Columns
    parsed_name = db.Column(db.String(120))
    parsed_email = db.Column(db.String(120))
    parsed_phone = db.Column(db.String(30))
    education_raw = db.Column(db.Text)      # JSON string list
    experience_raw = db.Column(db.Text)     # JSON string list
    skills_raw = db.Column(db.Text)         # JSON string list
    certifications_raw = db.Column(db.Text) # JSON string list
    
    # Relationships
    reports = db.relationship('ATSReport', backref='resume', lazy=True, cascade='all, delete-orphan')

    # Utility properties to handle JSON conversion transparently
    @property
    def education(self):
        return json.loads(self.education_raw) if self.education_raw else []
    @education.setter
    def education(self, value):
        self.education_raw = json.dumps(value)

    @property
    def experience(self):
        return json.loads(self.experience_raw) if self.experience_raw else []
    @experience.setter
    def experience(self, value):
        self.experience_raw = json.dumps(value)

    @property
    def skills(self):
        return json.loads(self.skills_raw) if self.skills_raw else []
    @skills.setter
    def skills(self, value):
        self.skills_raw = json.dumps(value)

    @property
    def certifications(self):
        return json.loads(self.certifications_raw) if self.certifications_raw else []
    @certifications.setter
    def certifications(self, value):
        self.certifications_raw = json.dumps(value)

    def __repr__(self):
        return f'<Resume {self.filename} for User {self.user_id}>'


class Skill(db.Model):
    __tablename__ = 'skills'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Languages', 'Frontend', 'Backend', 'Data Science', 'Soft Skills', etc.

    def __repr__(self):
        return f'<Skill {self.name} ({self.category})>'


class JobDescription(db.Model):
    __tablename__ = 'job_descriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150))
    raw_text = db.Column(db.Text, nullable=False)
    extracted_skills_raw = db.Column(db.Text) # JSON string list
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reports = db.relationship('ATSReport', backref='job_description', lazy=True, cascade='all, delete-orphan')

    @property
    def extracted_skills(self):
        return json.loads(self.extracted_skills_raw) if self.extracted_skills_raw else []
    @extracted_skills.setter
    def extracted_skills(self, value):
        self.extracted_skills_raw = json.dumps(value)

    def __repr__(self):
        return f'<JobDescription {self.title} at {self.company}>'


class ATSReport(db.Model):
    __tablename__ = 'ats_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_description_id = db.Column(db.Integer, db.ForeignKey('job_descriptions.id'), nullable=True)
    score = db.Column(db.Float, nullable=False) # ATS Percentage Score
    category = db.Column(db.String(30), nullable=False) # 'Excellent', 'Good', 'Average', 'Needs Improvement'
    
    # Matching breakdown
    matched_skills_raw = db.Column(db.Text)  # JSON string list
    missing_skills_raw = db.Column(db.Text)  # JSON string list
    suggestions_raw = db.Column(db.Text)     # JSON dict (verb suggestions, formatting, keyword advice)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def matched_skills(self):
        return json.loads(self.matched_skills_raw) if self.matched_skills_raw else []
    @matched_skills.setter
    def matched_skills(self, value):
        self.matched_skills_raw = json.dumps(value)

    @property
    def missing_skills(self):
        return json.loads(self.missing_skills_raw) if self.missing_skills_raw else []
    @missing_skills.setter
    def missing_skills(self, value):
        self.missing_skills_raw = json.dumps(value)

    @property
    def suggestions(self):
        return json.loads(self.suggestions_raw) if self.suggestions_raw else {}
    @suggestions.setter
    def suggestions(self, value):
        self.suggestions_raw = json.dumps(value)

    def __repr__(self):
        return f'<ATSReport Score={self.score}% Category={self.category}>'


class JobPosting(db.Model):
    __tablename__ = 'job_postings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    skills_required_raw = db.Column(db.Text) # JSON list
    url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def skills_required(self):
        return json.loads(self.skills_required_raw) if self.skills_required_raw else []
    @skills_required.setter
    def skills_required(self, value):
        self.skills_required_raw = json.dumps(value)

    def __repr__(self):
        return f'<JobPosting {self.title} at {self.company}>'
