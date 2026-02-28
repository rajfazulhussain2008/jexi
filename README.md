# JEXI - Personal AI Life OS

## 🚀 Quick Start

### Option 1: Setup and Start (Recommended)
Double-click `setup_and_start.bat` to:
- ✅ Verify installation
- 🚀 Start the development server
- 🌐 Open http://localhost:8080

### Option 2: Start Only
Double-click `start_jexi.bat` to start the server directly.

### Option 3: Frontend Only
Double-click `start_frontend.bat` to serve only the frontend.

## 📋 Prerequisites

1. **Python 3.7+** installed
2. **Supabase project** set up with environment variables configured
3. **Frontend directory** exists with your HTML/CSS/JS files

## 🔧 Configuration

Before running, ensure you have:

1. **Set up Supabase Database**
   - Go to your Supabase dashboard
   - Run the SQL from `backend/setup_supabase.sql`

2. **Environment Variables** (in `backend/.env`)
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-key
   SUPABASE_ANON_KEY=your-anon-key
   ```

## 🌐 Access

Once running, open your browser to:
- **Main App**: http://localhost:8080
- **API Health**: http://localhost:8080/health

## 🛑 Troubleshooting

- **Port 8080 in use**: The script will automatically try the next available port
- **Frontend not found**: Ensure you're running from the correct directory
- **Python not found**: Install Python 3.7+ and add to PATH

## 📁 Project Structure

```
jexi/
├── backend/           # API server and configuration
│   ├── .env           # Environment variables
│   ├── dev_server.py   # Development server
│   └── setup_supabase.sql  # Database setup
├── frontend/          # Web application
│   ├── index.html
│   ├── css/
│   └── js/
└── *.bat             # Batch files for easy startup
```

## 🎯 Features

- ✅ Supabase Authentication
- ✅ Real-time Database
- ✅ Accessible UI (WCAG 2.1 AA)
- ✅ Cross-browser compatible
- ✅ Mobile responsive

Enjoy your JEXI Personal AI Life OS! 🤖✨
