from flask_restful import Resource
from flask import request, current_app
from datetime import datetime, timezone
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from models import db, Report, StatusUpdate

class ReportStatusUpdateResource(Resource):
    @jwt_required()
    def post(self, report_id):
        try:
            # Authorization
            claims = get_jwt()
            if not claims.get("is_admin"):
                return {"message": "Admin access required"}, 403

            # Validate input
            data = request.get_json()
            new_status = data.get("status")
            if not new_status:
                return {"message": "Status is required"}, 400
            
            if new_status not in Report.VALID_STATUSES:
                return {
                    "message": f"Invalid status. Valid options: {Report.VALID_STATUSES}"
                }, 400

            # Get report
            report = Report.query.get(report_id)
            if not report:
                return {"message": "Report not found"}, 404

            # Create status update
            status_update = StatusUpdate(
                report_id=report.id,
                updated_by=claims["username"],  # From JWT
                status=new_status,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Sync report status
            report.status = new_status
            report.updated_at = datetime.now(timezone.utc)

            db.session.add(status_update)
            db.session.commit()

            return {
                "message": "Status updated successfully",
                "data": {
                    "report_id": report.id,
                    "new_status": new_status,
                    "timestamp": status_update.timestamp.isoformat()
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Status update failed")
            return {"message": "Internal server error"}, 500