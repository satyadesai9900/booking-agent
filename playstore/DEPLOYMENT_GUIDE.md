# MantaBooking — Complete Google Play Store Deployment Guide

This guide walks you through the complete end-to-end process of deploying the **MantaBooking** cloud backend and generating the signed **Android App Bundle (.aab)** ready for upload to the **Google Play Console**.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│               Android Smartphone / Tablet              │
│       MantaBooking App (com.mantabooking.app)          │
│       Target SDK 34 (Android 14/15 Ready)              │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS / TLS 1.3
                            ▼
┌────────────────────────────────────────────────────────┐
│             Production Cloud Backend                   │
│        (Render.com / Railway / Fly.io / VPS)           │
│  • Flask + Gunicorn Python Application                 │
│  • LangGraph AI Concierge & Direct Link Generator      │
│  • PWA Shell & Static Manifest / Service Worker        │
│  • Digital Asset Links (/.well-known/assetlinks.json)  │
│  • Public Privacy Policy (/privacy)                    │
└───────────────────────────┬────────────────────────────┘
                            │ Direct Verified Handoff
                            ▼
┌────────────────────────────────────────────────────────┐
│            Official Carrier & Booking Portals          │
│  • IRCTC / Indian Railways (Official 10-digit PNR)     │
│  • IndiGo / Air India / Emirates / Skyscanner          │
│  • Booking.com / Agoda / BookMyShow / Uber             │
└────────────────────────────────────────────────────────┘
```

---

## Step 1: Deploy the Cloud Backend (HTTPS Required)

Google Play Store apps require a live public HTTPS endpoint. You can host MantaBooking for free or low cost on **Render.com**, **Railway.app**, **Fly.io**, or any cloud VPS.

### Option A: 1-Click Deploy on Render.com (Recommended)

1. Push this repository to your GitHub account (`git push origin main`).
2. Go to [https://dashboard.render.com](https://dashboard.render.com) and click **New + > Blueprint**.
3. Select your GitHub repository. Render will automatically detect the provided [`render.yaml`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/render.yaml) and [`Dockerfile`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/Dockerfile).
4. In the Environment Variables settings, configure:
   - `GEMINI_API_KEY`: *(Your Google Gemini API Key)*
   - `FLASK_ENV`: `production`
   - `SESSION_SECRET`: *(A random secure string for user auth sessions)*
5. Click **Apply**. Render will build and deploy your container in ~2 minutes.
6. Your live URL will look like:
   `https://mantabooking.onrender.com`

### Verifying Cloud Deployment Health:
Open the following URLs in your browser to confirm everything is live:
- `https://your-app.onrender.com/` *(Main App & Landing Page)*
- `https://your-app.onrender.com/manifest.json` *(Web App Manifest)*
- `https://your-app.onrender.com/privacy` *(Mandatory Play Store Privacy Policy)*
- `https://your-app.onrender.com/.well-known/assetlinks.json` *(Asset Links)*

---

## Step 2: Build the Signed Android App Bundle (`.aab`)

You have **two seamless methods** to build the final Google Play `.aab` package:

### Method 1: Cloud Build via PWABuilder (Fastest — No Android Studio Needed)

This is the official Google & Microsoft open-source tool for generating store-ready Trusted Web Activities:

1. Open [https://www.pwabuilder.com](https://www.pwabuilder.com).
2. Enter your live backend URL (e.g., `https://mantabooking.onrender.com`) and click **Start**.
3. PWABuilder will test your PWA score (Manifest, Service Worker, HTTPS, and Icons will all pass with 100%).
4. Click **Package for Stores** and select **Google Play**.
5. Configure package settings:
   - **Package ID**: `com.mantabooking.app`
   - **App Name**: `MantaBooking`
   - **Short Name**: `MantaBooking`
   - **Display Mode**: `Standalone`
   - **Theme Color**: `#0B0F19`
   - **Background Color**: `#060911`
   - **Signing Key**: Select *Generate New Key* (or upload your existing keystore). **Download and save this keystore safely!**
6. Click **Generate Package**.
7. Download the `.zip` archive. Inside you will find:
   - `app-release.aab` *(This is the file you upload to Google Play Console)*
   - `assetlinks.json` *(Contains your digital asset links SHA-256)*

---

### Method 2: Local Native Build via Android Studio

If you prefer building locally using the included [`android/`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/android) project:

1. Open **Android Studio** and choose **Open**, then select the `android/` folder in this repo.
2. If your production domain is different, verify the target URL in:
   [`android/app/src/main/java/com/mantabooking/app/MainActivity.java`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/android/app/src/main/java/com/mantabooking/app/MainActivity.java) (Line 38).
3. In Android Studio's top menu, click:
   **Build > Generate Signed Bundle / APK...**
4. Select **Android App Bundle (.aab)** and click **Next**.
5. Key store path:
   - Click **Create new...**
   - Choose a file location (e.g. `mantabooking-release.keystore`).
   - Enter passwords, alias name (`mantabooking`), and validity (25+ years).
   - Enter your Organization / Name details.
6. Click **Next**, choose build variant **release**, and click **Finish**.
7. Your signed bundle is generated at:
   `android/app/release/app-release.aab`.

---

## Step 3: Configure Digital Asset Links (TWA Fullscreen Mode)

To ensure the Android app opens in seamless fullscreen app mode without any browser URL bar:

1. Get your release key's SHA-256 fingerprint:
   ```powershell
   keytool -list -v -keystore path/to/mantabooking-release.keystore -alias mantabooking
   ```
2. Copy the `SHA256: XX:XX:XX:...` fingerprint.
3. Open [`frontend/.well-known/assetlinks.json`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/frontend/.well-known/assetlinks.json) and paste your SHA-256 in the `sha256_cert_fingerprints` array.
4. If you deploy with Google Play App Signing (recommended), copy the SHA-256 provided under **Play Console > Release > Setup > App Integrity** and add it as well.
5. Deploy the updated file to your backend so `https://your-domain.onrender.com/.well-known/assetlinks.json` returns it.

---

## Step 4: Google Play Console Step-by-Step Publishing

### 1. Create App
1. Log in to the [Google Play Console](https://play.google.com/console).
2. Click **Create app**:
   - **App name**: `MantaBooking - AI Travel Hub`
   - **Default language**: `English (United States)`
   - **App or Game**: `App`
   - **Free or Paid**: `Free`
   - Accept Declarations and click **Create app**.

### 2. Complete "Set up your app" Tasks
Complete each required item in the dashboard:
1. **Privacy Policy**: Enter your live URL: `https://your-domain.onrender.com/privacy`
2. **App Access**: Choose *"All or some functionality is restricted"* -> Click *Add instructions*:
   - Title: `Demo User Access`
   - Instructions: *"Reviewers can click the '1-Click Satya Desai (Demo Access)' button on the sign-in modal for immediate full access, or register any email."*
3. **Ads**: Select *"No, my app does not contain ads"*.
4. **Content Rating**: Start the questionnaire:
   - Refer to Section 5 of [`playstore/STORE_LISTING.md`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/playstore/STORE_LISTING.md) for the exact responses.
   - Result will be **PEGI 3 / Everyone**.
5. **Target Audience**: Select **18 and over** (or 13+).
6. **News Apps**: Select *"No"*.
7. **COVID-19 Contact Tracing**: Select *"No"*.
8. **Data Safety**:
   - Refer to Section 6 of [`playstore/STORE_LISTING.md`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/playstore/STORE_LISTING.md) for full questionnaire details (encrypted in transit, user data deletion support).
9. **Financial Features**: Select *"App does not provide financial services or in-app payments"*.

### 3. Store Listing & Media Assets
Go to **Grow > Store presence > Main store listing**:
1. Copy **App Name**, **Short description**, and **Full description** directly from [`playstore/STORE_LISTING.md`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/playstore/STORE_LISTING.md).
2. **App Icon**: Upload [`playstore/icon_512x512.png`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/playstore/icon_512x512.png).
3. **Feature Graphic**: Upload [`playstore/feature_graphic_1024x500.png`](file:///c:/Users/satya/OneDrive/Desktop/langgraph/playstore/feature_graphic_1024x500.png).
4. **Phone Screenshots**: Take 2 to 4 screenshots of the app in mobile view (landing page, flights studio, trains studio, chat assistant) and upload them.
5. Click **Save**.

### 4. Create and Roll Out Release
1. Navigate to **Release > Production** (or start with **Internal testing** to test on your own phone first).
2. Click **Create new release**.
3. Under **App bundles**, upload your signed `app-release.aab` file.
4. Enter release name (e.g., `1.0.0 (Initial Release)`).
5. Release notes:
   ```text
   Initial launch of MantaBooking: AI-powered travel discovery, flight searches, IRCTC train availability, hotel comparisons, and direct carrier checkout links.
   ```
6. Click **Next**, review summary, and click **Start rollout to Production**!

Google reviews the submission (typically 24 to 72 hours for new accounts), after which **MantaBooking** will be live for billions of Android users worldwide on Google Play.
