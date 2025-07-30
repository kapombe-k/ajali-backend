
from flask_restful import Resource
from flask import request
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Report, StatusUpdate, User 

class ReportStatusUpdateResource(Resource):

    @jwt_required()
    def post(self, report_id):
        # Get current user identity from JWT token
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        # Check if user exists and is admin
        if not user or not user.is_admin:
            return {"error": "Admin access required"}, 403

        # Parse request data
        data = request.get_json()
        new_status = data.get('status')
        updated_by = data.get('updated_by')

        # Validate status
        if new_status not in ['under investigation', 'rejected', 'resolved']:
            return {"error": "Invalid status"}, 400

        # Admin username must be provided - you can decide if you want to fetch it from the user instead
        if not updated_by:
            return {"error": "updated_by is required"}, 400

        # Validate report exists
        report = Report.query.get(report_id)
        if not report:
            return {"error": "Report not found"}, 404

        try:
            # Create new StatusUpdate with the given data
            status_update = StatusUpdate(
                report_id=report_id,
                updated_by=updated_by,
                status=new_status,
                timestamp=datetime.utcnow()
            )
            db.session.add(status_update)
            db.session.commit()
            return {"message": f"Report status updated to '{new_status}'"}, 200

        except Exception as e:
            return {"error": str(e)}, 400


