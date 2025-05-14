# Deploying the Schedule Planner to Render

This guide provides step-by-step instructions to deploy the Schedule Planner application to Render's free tier.

## Prerequisites

1. A [Render](https://render.com/) account
2. Your Schedule Planner repository on GitHub (or other Git provider)

## Deployment Steps

### 1. Set up a New Web Service

1. Log in to your Render account
2. Click the "New +" button in the dashboard
3. Select "Web Service"
4. Connect your GitHub repository (you may need to authorize Render)
5. Select the repository containing your Schedule Planner application

### 2. Configure the Web Service

Fill in the following settings:

- **Name**: `schedule-planner` (or a name of your choice)
- **Region**: Choose the region closest to your users
- **Branch**: `main` (or your default branch)
- **Root Directory**: Leave empty
- **Runtime**: `Python 3`
- **Build Command**: `./build.sh`
- **Start Command**: `gunicorn app:app`

### 3. Set Environment Variables

Click on the "Advanced" button and add the following environment variables:

- `FLASK_APP`: `app.py`
- `FLASK_ENV`: `production`
- `RENDER`: `true`
- `SECRET_KEY`: [Generate a secure random key]
- `SENDGRID_API_KEY`: [Your SendGrid API key]
- `SENDGRID_FROM_EMAIL`: [Your verified sender email]

### 4. Set Resource Type

Choose the "Free" plan for testing purposes.

### 5. Create Web Service

Click the "Create Web Service" button to start the deployment process.

## Monitoring Deployment

- Render will now clone your repository and start building the application
- You can monitor the build process in the "Logs" tab
- The build may take several minutes to complete

## Testing the Deployment

Once the deployment is complete:
1. Click on the URL provided by Render (e.g., `https://schedule-planner.onrender.com`)
2. Verify that the application is working correctly
3. Test all key features, especially PDF generation

## Troubleshooting

If you encounter issues with the deployment:

1. Check the deployment logs for errors
2. Verify that all environment variables are correctly set
3. Ensure that the `build.sh` script has execute permissions (`chmod +x build.sh`)
4. If needed, restart the service from the Render dashboard

## Database Persistence

Note that Render's free tier doesn't include persistent database storage. If you need to maintain data between restarts:

1. Consider upgrading to a paid plan with a persistent disk
2. Or implement a solution to backup/restore data using an external storage service

## Further Customization

For production deployments, consider:
- Setting up a custom domain
- Configuring SSL certificates
- Adding monitoring and alerts
- Setting up automatic database backups

## Limitations on Free Tier

### PDF Generation

The free tier of Render has several limitations that affect this application:

1. **Read-only filesystem**: The container runs in a read-only environment, which prevents installing system packages like wkhtmltopdf.

2. **PDF Generation**: PDF generation functionality will be limited on Render's free tier. The application includes a fallback mechanism that:
   - Checks if wkhtmltopdf is available on the system
   - If not, uses a simple wrapper script that creates empty PDF files
   - In worst case, returns a plain text message indicating that PDF generation is not available

For full PDF functionality, consider:
- Using the application locally
- Upgrading to Render's paid tier
- Exploring alternative PDF generation options like client-side PDF generation 