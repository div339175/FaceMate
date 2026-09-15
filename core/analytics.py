"""
🧠 AI-POWERED ATTENDANCE ANALYTICS
Advanced analytics and insights for FaceMate system
"""

import numpy as np
from datetime import datetime, timedelta
from django.db.models import Count, Q
from collections import defaultdict
import json

def generate_attendance_insights(student_records, days=30):
    """
    Generate AI-powered insights from attendance data
    """
    insights = {
        'summary': {},
        'predictions': {},
        'recommendations': [],
        'trends': {},
        'risk_alerts': []
    }
    
    if not student_records:
        return insights
    
    # Calculate attendance patterns
    total_days = days
    
    for student in student_records:
        attendance_count = student.attendance_count if hasattr(student, 'attendance_count') else 0
        attendance_rate = (attendance_count / total_days) * 100 if total_days > 0 else 0
        
        # Risk assessment using AI-like scoring
        risk_score = calculate_risk_score(attendance_rate, attendance_count)
        
        insights['summary'][student.enrollment_number] = {
            'name': student.name,
            'attendance_rate': round(attendance_rate, 1),
            'total_present': attendance_count,
            'risk_score': risk_score,
            'status': get_attendance_status(attendance_rate)
        }
        
        # Generate predictions
        predicted_rate = predict_future_attendance(attendance_rate, attendance_count)
        insights['predictions'][student.enrollment_number] = {
            'predicted_month_end': round(predicted_rate, 1),
            'improvement_needed': max(0, 75 - predicted_rate)  # Target 75%
        }
        
        # Risk alerts
        if risk_score > 70:
            insights['risk_alerts'].append({
                'student': student.name,
                'enrollment': student.enrollment_number,
                'risk_level': 'HIGH' if risk_score > 85 else 'MEDIUM',
                'message': f'Attendance rate {attendance_rate:.1f}% - requires intervention'
            })
    
    # Class-wide insights
    avg_attendance = np.mean([s['attendance_rate'] for s in insights['summary'].values()])
    insights['class_summary'] = {
        'average_attendance': round(avg_attendance, 1),
        'students_at_risk': len(insights['risk_alerts']),
        'top_performers': len([s for s in insights['summary'].values() if s['attendance_rate'] > 90]),
        'needs_attention': len([s for s in insights['summary'].values() if s['attendance_rate'] < 75])
    }
    
    # Generate recommendations
    insights['recommendations'] = generate_recommendations(insights)
    
    return insights

def calculate_risk_score(attendance_rate, days_present):
    """
    AI-based risk scoring algorithm
    """
    base_score = max(0, 100 - attendance_rate)  # Higher score = higher risk
    
    # Adjust for consistency (penalize sporadic attendance)
    if days_present > 0:
        consistency_penalty = abs(attendance_rate - 80) * 0.5
        base_score += consistency_penalty
    
    return min(100, base_score)

def predict_future_attendance(current_rate, days_present):
    """
    Simple trend-based prediction
    """
    if days_present < 5:
        return current_rate  # Not enough data
    
    # Simulate trend analysis (in real implementation, use time series)
    trend_factor = 1.0
    if current_rate > 80:
        trend_factor = 0.95  # Slight decline expected
    elif current_rate < 60:
        trend_factor = 1.1   # Intervention effect
    
    return min(100, current_rate * trend_factor)

def get_attendance_status(rate):
    """
    Categorize attendance performance
    """
    if rate >= 90:
        return 'EXCELLENT'
    elif rate >= 80:
        return 'GOOD'
    elif rate >= 70:
        return 'AVERAGE'
    elif rate >= 60:
        return 'BELOW_AVERAGE'
    else:
        return 'CRITICAL'

def generate_recommendations(insights):
    """
    AI-generated actionable recommendations
    """
    recommendations = []
    
    class_avg = insights['class_summary']['average_attendance']
    risk_count = insights['class_summary']['students_at_risk']
    
    if class_avg < 75:
        recommendations.append({
            'type': 'CLASS_INTERVENTION',
            'priority': 'HIGH',
            'message': f'Class average ({class_avg:.1f}%) below target. Consider class-wide engagement activities.'
        })
    
    if risk_count > 3:
        recommendations.append({
            'type': 'COUNSELING',
            'priority': 'MEDIUM',
            'message': f'{risk_count} students at risk. Schedule individual counseling sessions.'
        })
    
    # Positive reinforcement
    top_performers = insights['class_summary']['top_performers']
    if top_performers > 0:
        recommendations.append({
            'type': 'RECOGNITION',
            'priority': 'LOW',
            'message': f'Recognize {top_performers} high-performing students to motivate others.'
        })
    
    return recommendations

def generate_smart_report(insights):
    """
    Generate natural language attendance report
    """
    class_summary = insights['class_summary']
    
    report = f"""
    📊 SMART ATTENDANCE ANALYSIS REPORT
    
    🎯 Overall Performance: {class_summary['average_attendance']:.1f}% class average
    
    ✅ High Performers: {class_summary['top_performers']} students (>90% attendance)
    ⚠️  At Risk: {class_summary['students_at_risk']} students need attention
    
    🔍 Key Insights:
    """
    
    if class_summary['average_attendance'] > 85:
        report += "• Excellent class engagement levels\n"
    elif class_summary['average_attendance'] > 75:
        report += "• Good overall attendance with room for improvement\n"
    else:
        report += "• Class requires immediate intervention strategies\n"
    
    # Add recommendations
    for rec in insights['recommendations']:
        report += f"• {rec['message']}\n"
    
    return report

def export_analytics_data(insights):
    """
    Export analytics for external systems
    """
    export_data = {
        'generated_at': datetime.now().isoformat(),
        'analytics_version': '1.0',
        'insights': insights,
        'metadata': {
            'total_students_analyzed': len(insights['summary']),
            'analysis_period_days': 30,
            'ai_model': 'FaceMate Analytics Engine v1.0'
        }
    }
    
    return json.dumps(export_data, indent=2)