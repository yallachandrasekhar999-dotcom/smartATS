from app import app
from models import db, Skill, JobPosting, User
from flask_bcrypt import Bcrypt
import json

def seed_database():
    with app.app_context():
        print("Re-creating all tables...")
        db.drop_all()
        db.create_all()
        
        bcrypt = Bcrypt()
        
        # 1. Seed Admin & Recruiter Users
        print("Seeding initial users...")
        admin_pass = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = User(
            username='admin',
            email='admin@resumeanalyzer.com',
            password_hash=admin_pass,
            role='admin'
        )
        
        recruiter_pass = bcrypt.generate_password_hash('recruiter123').decode('utf-8')
        recruiter = User(
            username='recruiter_john',
            email='recruiter@resumeanalyzer.com',
            password_hash=recruiter_pass,
            role='recruiter'
        )
        
        candidate_pass = bcrypt.generate_password_hash('candidate123').decode('utf-8')
        candidate = User(
            username='candidate_jane',
            email='jane@gmail.com',
            password_hash=candidate_pass,
            role='user'
        )
        
        db.session.add(admin)
        db.session.add(recruiter)
        db.session.add(candidate)
        
        # 2. Seed Skills Catalog
        print("Seeding skills database...")
        from parser import SKILL_DICTIONARY
        for category, skills in SKILL_DICTIONARY.items():
            for skill_name in skills:
                # Format skills nicely
                display_name = skill_name
                if skill_name in ['c++', 'c#', 'ci/cd', 'aws', 'gcp', 'mvc', 'oop', 'tdd', 'api', 'rest api', 'soap', 'html', 'css', 'sql', 'r']:
                    display_name = skill_name.upper()
                elif skill_name in ['react', 'node', 'vue', 'next', 'nuxt', 'express']:
                    display_name = skill_name.title() + ".js"
                else:
                    display_name = skill_name.title()
                
                # Deduplicate and add
                existing = Skill.query.filter_by(name=display_name).first()
                if not existing:
                    db.session.add(Skill(name=display_name, category=category))
                    
        # 3. Seed Job Postings
        print("Seeding sample job postings...")
        jobs = [
            {
                'title': 'Junior Python Developer',
                'company': 'Tech Solutions Inc.',
                'location': 'New York, NY (Hybrid)',
                'description': 'We are looking for a Python Developer to join our backend team. You will write REST APIs, work with PostgreSQL database, and use Docker for deployment.',
                'skills_required': ['Python', 'Flask', 'SQL', 'MySQL', 'Docker', 'REST API', 'Git'],
                'url': 'https://example.com/jobs/python-dev-1'
            },
            {
                'title': 'Frontend Engineer (React)',
                'company': 'SaaSify Web Solutions',
                'location': 'Remote',
                'description': 'Join our dynamic frontend team building glassmorphism interfaces in React. Excellent TypeScript and CSS styling knowledge required.',
                'skills_required': ['HTML', 'CSS', 'JavaScript', 'TypeScript', 'React.js', 'Redux', 'Tailwind CSS', 'Figma'],
                'url': 'https://example.com/jobs/frontend-react-2'
            },
            {
                'title': 'DevOps Cloud Engineer',
                'company': 'CloudScale Systems',
                'location': 'Austin, TX',
                'description': 'Manage our cloud server infrastructure. Setup Git/Github CI/CD pipelines, Docker containers, Kubernetes orchestrations, and automate deployments on AWS.',
                'skills_required': ['AWS', 'Docker', 'Kubernetes', 'CI/CD', 'Git', 'GitHub', 'Linux', 'Terraform'],
                'url': 'https://example.com/jobs/devops-cloud-3'
            },
            {
                'title': 'Data Scientist & ML Analyst',
                'company': 'DataInsight Corp',
                'location': 'San Francisco, CA',
                'description': 'Run machine learning operations, analyze high-volume business data, and build predictive models in Python. Experience with Pandas and TensorFlow is mandatory.',
                'skills_required': ['Python', 'SQL', 'TensorFlow', 'Scikit-learn', 'Pandas', 'NumPy', 'Jupyter', 'Tableau'],
                'url': 'https://example.com/jobs/data-scientist-4'
            },
            {
                'title': 'Full Stack Engineer',
                'company': 'Enterprise Hub LLC',
                'location': 'Chicago, IL (Onsite)',
                'description': 'Develop scalable end-to-end applications. Candidate should be comfortable writing React on the frontend and Node/Express on the backend, deploying on AWS.',
                'skills_required': ['HTML', 'CSS', 'JavaScript', 'React.js', 'Node.js', 'Express.js', 'MongoDB', 'AWS', 'Git', 'Agile'],
                'url': 'https://example.com/jobs/fullstack-node-5'
            }
        ]
        
        for job_data in jobs:
            db.session.add(JobPosting(
                title=job_data['title'],
                company=job_data['company'],
                location=job_data['location'],
                description=job_data['description'],
                skills_required=job_data['skills_required'],
                url=job_data['url']
            ))
            
        db.session.commit()
        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()
