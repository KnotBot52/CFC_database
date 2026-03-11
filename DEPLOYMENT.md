# Deployment Guide: Cruelty Free Compass Database

This guide explains how to deploy your Hugo site to Netlify and configure your custom domain (`database.crueltyfreecompass.com`).

## Step 1: Deploying to Netlify

1. **Push your code to a Git repository** (GitHub, GitLab, or Bitbucket).
2. **Log in to [Netlify](https://app.netlify.com/).**
3. Click **Add new site** -> **Import an existing project**.
4. Connect your Git provider and select the repository containing your Hugo site.
5. Netlify will automatically detect Hugo and use the build settings provided in the `netlify.toml` file located in the root directory.
6. Click **Deploy site**.

## Step 2: Configuring Your Custom Domain

Once the site is deployed on Netlify, you need to point `database.crueltyfreecompass.com` to your Netlify site.

1. In your Netlify site dashboard, go to **Domain management** -> **Domains**.
2. Click **Add custom domain** and enter `database.crueltyfreecompass.com`. Click **Verify** and then **Add domain**.
3. Netlify will assign a primary subdomain to your project (e.g., `cfc-database.netlify.app`). Keep this URL handy.

### The Recommended Approach: Using a CNAME Record

Since you are setting up a *subdomain* (`database`), the most robust approach is to create a CNAME record.

1. Log in to the domain registrar where you purchased `crueltyfreecompass.com` (e.g., Namecheap, GoDaddy, Squarespace, Cloudflare).
2. Navigate to your domain's **DNS Management** or **DNS Records** section.
3. Add a new record with the following details:
   * **Type:** `CNAME`
   * **Name / Host:** `database`
   * **Value / Target / Points to:** `[your-site-name].netlify.app` (The Netlify subdomain from step 2).
   * **TTL:** `Default` or `3600` (1 Hour).
4. Save the record.

## Step 3: Automatic SSL/HTTPS Certificate

Once your DNS changes propagate across the internet (this usually takes 5 to 30 minutes, but can take up to 24 hours), Netlify will automatically generate a free Let's Encrypt SSL certificate.

1. Go back to your Netlify **Domain Management** settings.
2. Scroll down to the **HTTPS** section.
3. Once the DNS verification completes, your certificate will be provisioned.

Your database will then be securely accessible at **https://database.crueltyfreecompass.com/**!
