import unittest
import os
import json
from app import app, db
from models import User, Resume, JobDescription, ATSReport, JobPosting
from parser import extract_name, extract_contact_info, extract_skills, extract_sections
from recommender import calculate_ats_score, calculate_general_ats_score, analyze_resume_suggestions

class TestResumeAnalyzer(unittest.TestCase):
    
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        
        with app.app_context():
            from sqlalchemy import create_engine
            db.engines[None] = create_engine('sqlite:///:memory:')
            db.create_all()
            # Seed a test user
            self.test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash='hashed_pass',
                role='user'
            )
            db.session.add(self.test_user)
            db.session.commit()
            self.user_id = self.test_user.id
            
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # ----------------------------------------------------
    # Parser Unit Tests
    # ----------------------------------------------------

    def test_contact_extraction(self):
        test_text = "John Doe\nEmail: john.doe@gmail.com\nPhone: +1-555-019-2834\nSoftware Engineer"
        email, phone = extract_contact_info(test_text)
        self.assertEqual(email, "john.doe@gmail.com")
        self.assertIn("555", phone)

    def test_name_heuristics(self):
        test_text = "Alice Smith\n\nSoftware Developer\nEmail: alice@gmail.com"
        name = extract_name(test_text)
        self.assertEqual(name, "Alice Smith")

    def test_skills_extraction(self):
        test_text = "Experienced Developer with expertise in python, react, postgresql database, and docker."
        skills = extract_skills(test_text)
        self.assertIn("Python", skills)
        self.assertIn("React.js", skills)
        self.assertIn("PostgreSQL", skills)
        self.assertIn("Docker", skills)

    def test_sections_extraction(self):
        test_text = """
        John Doe
        
        EXPERIENCE
        Worked as a Software Engineer at Tech Corp.
        Developed microservices using Flask.
        
        EDUCATION
        B.S. in Computer Science at State University.
        
        CERTIFICATIONS
        AWS Cloud Practitioner.
        """
        sections = extract_sections(test_text)
        self.assertIn("Education", sections)
        self.assertIn("Experience", sections)
        self.assertIn("Certifications", sections)
        self.assertTrue(any("State University" in line for line in sections["Education"]))
        self.assertTrue(any("Tech Corp" in line for line in sections["Experience"]))

    # ----------------------------------------------------
    # Recommender Unit Tests
    # ----------------------------------------------------

    def test_ats_score_calculation(self):
        resume_data = {
            'skills': ['Python', 'Flask', 'SQL', 'Docker'],
            'raw_text': 'I have python and flask developer skills with SQL and docker container experience. Email: john@gmail.com Phone: 555-555-5555 Name: John Doe',
            'experience': ['Worked 2 years'],
            'education': ['B.S. CS'],
            'email': 'john@gmail.com',
            'phone': '555-555-5555',
            'name': 'John Doe'
        }
        
        # Perfect JD match (100% of skills matching)
        jd_data_perfect = {
            'skills': ['Python', 'Flask', 'SQL', 'Docker'],
            'raw_text': 'Looking for a python developer who knows flask, sql, and docker.'
        }
        
        result_perfect = calculate_ats_score(resume_data, jd_data_perfect)
        self.assertGreaterEqual(result_perfect['score'], 80.0) # High match
        self.assertEqual(result_perfect['category'], 'Good' if result_perfect['score'] < 90 else 'Excellent')
        
        # Poor JD match
        jd_data_poor = {
            'skills': ['Kubernetes', 'Java', 'React.js', 'Spring Boot', 'AWS', 'Vue.js'],
            'raw_text': 'Required skills: kubernetes, java, react.js, spring boot, aws, vue.js'
        }
        result_poor = calculate_ats_score(resume_data, jd_data_poor)
        self.assertLess(result_poor['score'], 50.0) # Poor match
        self.assertEqual(result_poor['category'], 'Needs Improvement')

    def test_verb_suggestions(self):
        resume_data = {
            'raw_text': 'I managed a team and helped build docker containers. I did python coding.',
            'skills': [],
            'experience': [],
            'education': []
        }
        sug = analyze_resume_suggestions(resume_data)
        weak_detected = [v['weak'] for v in sug['verb_replacements']]
        self.assertIn('managed', weak_detected)
        self.assertIn('helped', weak_detected)
        self.assertIn('did', weak_detected)

    # ----------------------------------------------------
    # Flask Routes & Authentication Integration Tests
    # ----------------------------------------------------

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Conquer the Applicant Tracking System", response.data)

    def test_login_page(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sign In", response.data)

    def test_register_page(self):
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Create Free Account", response.data)

    def test_admin_dashboard_redirect(self):
        # Unauthenticated access to /admin should redirect to /admin/login
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.location)

    def test_admin_login_unauthorized(self):
        # Log in with non-admin user
        response = self.client.post('/admin/login', data={
            'email': 'test@example.com',
            'password': 'hashed_pass'
        }, follow_redirects=True)
        self.assertIn(b"You are not Authorized to this", response.data)

    def test_admin_login_success(self):
        # Seed an admin user
        with app.app_context():
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt()
            admin_user = User(
                username='adminuser',
                email='admin@example.com',
                password_hash=bcrypt.generate_password_hash('adminpwd').decode('utf-8'),
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()

        # Log in with admin user
        response = self.client.post('/admin/login', data={
            'email': 'admin@example.com',
            'password': 'adminpwd'
        }, follow_redirects=True)
        self.assertIn(b"Welcome to the Admin Console!", response.data)
        self.assertIn(b"Admin Control Panel", response.data)

    def test_calculate_general_ats_score(self):
        resume_data = {
            'skills': ['Python', 'Flask', 'SQL', 'Docker', 'Git'],
            'raw_text': 'I have python and flask developer skills. Email: john@gmail.com Phone: 555-555-5555 Name: John Doe',
            'experience': ['Worked 2 years'],
            'education': ['B.S. CS'],
            'email': 'john@gmail.com',
            'phone': '555-555-5555',
            'name': 'John Doe'
        }
        res = calculate_general_ats_score(resume_data)
        self.assertGreaterEqual(res['score'], 50.0)
        self.assertIn('Git', res['matched_skills'])
        self.assertIn('AWS', res['missing_skills']) # Missing from resume but in standard benchmarks

    def test_analyze_route_general(self):
        # Login test user
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user_id)
            sess['_fresh'] = True

        # Mock resume upload
        import io
        response = self.client.post('/analyze', data={
            'analysis_type': 'general',
            'resume_file': (io.BytesIO(b"John Doe\nEmail: john@gmail.com\nPhone: 555-555-5555\nSkills: python, git"), 'resume.pdf'),
            'track_version': 'on'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"General Software Benchmark", response.data)
        self.assertIn(b"ATS Score prediction completed successfully!", response.data)

    def test_analyze_route_jd(self):
        # Login test user
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user_id)
            sess['_fresh'] = True

        # Mock resume upload
        import io
        response = self.client.post('/analyze', data={
            'analysis_type': 'job_description',
            'resume_file': (io.BytesIO(b"John Doe\nEmail: john@gmail.com\nPhone: 555-555-5555\nSkills: python, git"), 'resume.pdf'),
            'job_description': 'We need a developer who knows python, docker, git.',
            'track_version': 'on'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Matched Target Profile", response.data)
        self.assertIn(b"ATS Score prediction completed successfully!", response.data)


if __name__ == '__main__':
    unittest.main()
