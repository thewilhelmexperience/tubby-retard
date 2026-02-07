#!/usr/bin/env node
/**
 * Cloudflare Worker for Tubby Retard Story Submissions
 * 
 * This Worker receives form submissions from tubbyretard.com and forwards
 * sanitized data to OpenClaw's /hooks/agent endpoint for immediate script generation.
 * 
 * Deploy: wrangler deploy
 * 
 * Environment variables needed:
 * - OPENCLAW_HOOK_TOKEN: Secret token for OpenClaw webhook auth
 * - OPENCLAW_HOOK_URL: Full URL to OpenClaw /hooks/agent endpoint
 * - TELEGRAM_CHAT_ID: Your Telegram chat ID for notifications
 */

// Security: Characters to strip from user input
const DANGEROUS_CHARS = /[<>\"'`;|&$\{\}\[\]\\]/g;
const MAX_TITLE_LENGTH = 100;
const MAX_STORY_LENGTH = 2000;

/**
 * Sanitize user input - remove dangerous characters and limit length
 */
function sanitizeInput(input, maxLength) {
  if (!input || typeof input !== 'string') {
    return '';
  }
  
  // Strip HTML/script injection attempts
  let cleaned = input
    .replace(DANGEROUS_CHARS, '')  // Remove dangerous chars
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
    .replace(/<[^>]+>/g, ''); // Remove all HTML tags
  
  // Trim to max length
  return cleaned.trim().substring(0, maxLength);
}

/**
 * Validate that submission looks legitimate
 */
function isValidSubmission(title, story, location) {
  // Title must exist and be reasonable
  if (!title || title.length < 3 || title.length > MAX_TITLE_LENGTH) {
    return false;
  }
  
  // Story must exist and have some substance
  if (!story || story.length < 20 || story.length > MAX_STORY_LENGTH) {
    return false;
  }
  
  // Check for spam patterns
  const spamPatterns = [
    /http[s]?:\/\/\S+/gi,  // URLs (legitimate stories shouldn't need links)
    /buy\s+now/i,
    /click\s+here/i,
    /viagra|cialis|pills/i,
    /make\s+money/i,
    /\$\d+,?\d*\s*(million|k)/i,  // Money amounts
  ];
  
  const combinedText = `${title} ${story}`;
  for (const pattern of spamPatterns) {
    if (pattern.test(combinedText)) {
      return false;
    }
  }
  
  return true;
}

/**
 * Generate safe filename slug from title
 */
function generateSlug(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')  // Replace non-alphanumeric with dashes
    .replace(/^-+|-+$/g, '')       // Trim dashes
    .substring(0, 50);             // Limit length
}

export default {
  async fetch(request, env, ctx) {
    // Only accept POST requests
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { 
        status: 405,
        headers: { 'Allow': 'POST' }
      });
    }

    try {
      // Parse the form submission
      const formData = await request.json();
      
      // Extract fields (Formspree format or direct form POST)
      const rawTitle = formData.title || formData._title || formData['title'] || '';
      const rawStory = formData.story || formData._story || formData['story'] || formData.message || '';
      const rawLocation = formData.location || formData._location || formData['location'] || '';
      
      // Sanitize all inputs
      const title = sanitizeInput(rawTitle, MAX_TITLE_LENGTH);
      const story = sanitizeInput(rawStory, MAX_STORY_LENGTH);
      const location = sanitizeInput(rawLocation, 100);
      
      // Validate submission
      if (!isValidSubmission(title, story, location)) {
        console.log('Rejected invalid/spam submission:', { title: title.substring(0, 50) });
        return new Response(JSON.stringify({ 
          success: false, 
          error: 'Invalid submission - please provide a valid title and story' 
        }), { 
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      // Generate slug for tracking
      const slug = generateSlug(title);
      
      // Prepare message for OpenClaw
      const openclawMessage = {
        message: `📝 New TR Story Submission

**Title:** ${title}
**Location:** ${location || 'Not specified'}
**Slug:** ${slug}

**Story:**
${story}

---
Please generate a comic script for this story and save it to tr-website/scripts/comic-draft-${slug}.md
Include a suggested panel sequence (4 panels) with DALL-E prompts for each.
Mark the script as [DRAFT - PENDING REVIEW] in the header.`,
        name: "TR-Submission",
        channel: "telegram",
        to: env.TELEGRAM_CHAT_ID || "6285846217",
        deliver: true,
        wakeMode: "now",
        timeoutSeconds: 120
      };
      
      // Forward to OpenClaw
      const openclawResponse = await fetch(env.OPENCLAW_HOOK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${env.OPENCLAW_HOOK_TOKEN}`,
          'X-Openclaw-Token': env.OPENCLAW_HOOK_TOKEN
        },
        body: JSON.stringify(openclawMessage)
      });
      
      if (!openclawResponse.ok) {
        const errorText = await openclawResponse.text();
        console.error('OpenClaw hook failed:', errorText);
        
        // Return success to form anyway (don't expose backend issues to user)
        return new Response(JSON.stringify({ 
          success: true, 
          message: 'Submission received! Your story is being processed.' 
        }), { 
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      // Success response to the form/user
      return new Response(JSON.stringify({ 
        success: true, 
        message: 'Submission received! Your story has been sent for script generation.' 
      }), { 
        status: 200,
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST'
        }
      });
      
    } catch (error) {
      console.error('Worker error:', error);
      
      // Return generic error (don't expose internal details)
      return new Response(JSON.stringify({ 
        success: false, 
        error: 'Processing error - please try again later' 
      }), { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};
