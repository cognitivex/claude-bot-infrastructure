#!/usr/bin/env python3
"""
Claude Bot Status Web Application
A Flask web application for hosting bot status dashboard
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import threading
import time

app = Flask(__name__)

# Configuration
DATA_DIR = Path(os.getenv('STATUS_DATA_DIR', '/app/data'))
DATA_DIR.mkdir(exist_ok=True)

# In-memory storage for bot statuses
bot_statuses = {}
status_lock = threading.Lock()

# Bot status file paths
def get_bot_status_file(bot_id):
    return DATA_DIR / f"{bot_id}.json"

def load_existing_statuses():
    """Load existing status files on startup"""
    global bot_statuses
    
    for status_file in DATA_DIR.glob("*.json"):
        try:
            with open(status_file, 'r') as f:
                status = json.load(f)
                bot_id = status.get('bot_id', status_file.stem)
                
                with status_lock:
                    bot_statuses[bot_id] = status
                    
                print(f"✅ Loaded existing status for {bot_id}")
        except Exception as e:
            print(f"⚠️  Failed to load {status_file}: {e}")

def save_bot_status(bot_id, status):
    """Save bot status to file and memory"""
    try:
        # Save to file
        status_file = get_bot_status_file(bot_id)
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        # Update in-memory storage
        with status_lock:
            bot_statuses[bot_id] = status
        
        print(f"💾 Saved status for {bot_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to save status for {bot_id}: {e}")
        return False

def cleanup_old_statuses():
    """Remove statuses that haven't been updated in 1 hour"""
    cutoff_time = datetime.now() - timedelta(hours=1)
    
    with status_lock:
        expired_bots = []
        for bot_id, status in bot_statuses.items():
            try:
                last_update = datetime.fromisoformat(status['timestamp'].replace('Z', '+00:00'))
                if last_update < cutoff_time:
                    expired_bots.append(bot_id)
            except:
                # If timestamp is invalid, consider it expired
                expired_bots.append(bot_id)
        
        for bot_id in expired_bots:
            del bot_statuses[bot_id]
            # Also remove file
            try:
                get_bot_status_file(bot_id).unlink(missing_ok=True)
                print(f"🗑️  Removed expired status for {bot_id}")
            except:
                pass

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_all_status():
    """API endpoint to get all bot statuses"""
    with status_lock:
        statuses = list(bot_statuses.values())
    
    # Sort by status (active first)
    status_order = {'running': 0, 'healthy': 1, 'idle': 2, 'unhealthy': 3, 'offline': 4}
    statuses.sort(key=lambda x: status_order.get(x.get('status', 'offline'), 5))
    
    return jsonify({
        'statuses': statuses,
        'count': len(statuses),
        'last_updated': datetime.now().isoformat()
    })

@app.route('/api/status/<bot_id>')
def get_bot_status(bot_id):
    """API endpoint to get specific bot status"""
    with status_lock:
        status = bot_statuses.get(bot_id)
    
    if status:
        return jsonify(status)
    else:
        return jsonify({'error': 'Bot not found'}), 404

@app.route('/api/status/<bot_id>', methods=['POST'])
def update_bot_status(bot_id):
    """API endpoint for bots to update their status"""
    try:
        status_data = request.get_json()
        
        if not status_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Add server-side timestamp and bot_id
        status_data['bot_id'] = bot_id
        status_data['received_at'] = datetime.now().isoformat()
        
        # Validate required fields
        if 'timestamp' not in status_data:
            status_data['timestamp'] = datetime.now().isoformat()
        
        # Save the status
        if save_bot_status(bot_id, status_data):
            return jsonify({
                'success': True,
                'message': f'Status updated for {bot_id}',
                'timestamp': status_data['timestamp']
            })
        else:
            return jsonify({'error': 'Failed to save status'}), 500
            
    except Exception as e:
        print(f"❌ Error updating status for {bot_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_bots': len(bot_statuses),
        'uptime': 'running'
    })

@app.route('/api/bots')
def list_bots():
    """List all known bot IDs"""
    with status_lock:
        bot_ids = list(bot_statuses.keys())
    
    return jsonify({
        'bot_ids': bot_ids,
        'count': len(bot_ids)
    })

# Background cleanup task
def cleanup_task():
    """Background task to cleanup old statuses"""
    while True:
        try:
            cleanup_old_statuses()
            time.sleep(300)  # Run every 5 minutes
        except Exception as e:
            print(f"❌ Cleanup task error: {e}")
            time.sleep(60)  # Wait 1 minute on error

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🤖 Starting Claude Bot Status Web Application")
    print(f"📁 Data directory: {DATA_DIR}")
    
    # Load existing statuses
    load_existing_statuses()
    
    # Start cleanup background task
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()
    
    # Get configuration
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    print(f"🌐 Starting web server on {host}:{port}")
    print(f"🔗 Dashboard: http://{host}:{port}")
    print(f"📊 API: http://{host}:{port}/api/status")
    
    app.run(host=host, port=port, debug=debug)