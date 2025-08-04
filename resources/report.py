from flask_restful import Resource
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Report, MediaAttachment
from datetime import datetime, timezone
from supabase import create_client
import os

# Initialize Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

class ReportResource(Resource):
    @jwt_required()
    def get(self, report_id=None):
        current_user = get_jwt_identity()
        
        # Single report
        if report_id:
            report = Report.query.get_or_404(report_id)
            if report.user_id != current_user["id"] and current_user.get("role") != "admin":
                return {"message": "Unauthorized"}, 403
            return self._serialize_report(report)
        
        # All reports (admin gets all, users get their own)
        query = Report.query
        if current_user.get("role") != "admin":
            query = query.filter_by(user_id=current_user["id"])
            
        return [self._serialize_report(r) for r in query.all()], 200

    @jwt_required()
    def post(self):
        try:
            data = request.get_json()
            user_id = get_jwt_identity()["id"]
            
            # Validate
            required_fields = ["incident", "details", "latitude", "longitude"]
            if not all(field in data for field in required_fields):
                return {"message": f"Missing fields: {required_fields}"}, 400

            # Create report
            report = Report(
                user_id=user_id,
                incident=data["incident"],
                details=data["details"],
                latitude=data["latitude"],
                longitude=data["longitude"],
            )
            db.session.add(report)
            db.session.commit()
            
            return self._serialize_report(report), 201

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Report creation failed: {str(e)}")
            return {"message": "Report creation failed"}, 500

    @jwt_required()
    def delete(self, report_id):
        report = Report.query.get_or_404(report_id)
        current_user = get_jwt_identity()
        
        # Authorization
        if report.user_id != current_user["id"] and current_user.get("role") != "admin":
            return {"message": "Unauthorized"}, 403

        try:
            # Delete associated media from Supabase
            for media in report.media_attachments:
                supabase.storage.from_("report-media").remove([media.file_key])
            
            db.session.delete(report)
            db.session.commit()
            return {"message": "Report deleted"}, 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Deletion failed: {str(e)}")
            return {"message": "Deletion failed"}, 500

    def _serialize_report(self, report):
        return {
            "id": report.id,
            "title": report.incident,  # Frontend expects 'title'
            "description": report.details,
            "status": report.status or "pending",
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "media_urls": [
                supabase.storage.from_("report-media").get_public_url(m.file_key)
                for m in report.media_attachments
            ]
        }

class UserReportsResource(Resource):
    @jwt_required()
    def get(self, user_id):
        current_user = get_jwt_identity()
        if user_id != current_user["id"] and current_user.get("role") != "admin":
            return {"message": "Unauthorized"}, 403
            
        reports = Report.query.filter_by(user_id=user_id).all()
        return [ReportResource()._serialize_report(r) for r in reports], 200