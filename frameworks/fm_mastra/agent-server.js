import { Agent } from '@mastra/core/agent';
import { openai } from '@ai-sdk/openai';
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Load environment variables
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, '.env.local') });

const app = express();

// Middleware
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Default model configuration with environment variable support
const getModel = () => {
  const modelName = process.env.BBH_MODEL || 'gpt-4.1-nano';
  console.log(`Using model: ${modelName}`);
  return openai(modelName);
};

// Create the Mastra agent
const agent = new Agent({
  name: 'BBH-Reasoning-Agent',
  instructions: `You are an expert reasoning assistant specializing in solving complex multi-step problems. 

When given a problem:
1. Read the question carefully and understand what is being asked
2. Think through the problem step by step 
3. Show your reasoning process clearly
4. Provide your final answer

For multiple choice questions, always provide your answer in the format requested.
For other questions, be precise and direct in your response.

Focus on accuracy and clear logical reasoning.`,
  model: getModel()
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'mastra-bbh-server',
    model: process.env.BBH_MODEL || 'gpt-4.1-nano',
    timestamp: new Date().toISOString()
  });
});

// Main BBH reasoning endpoint
app.post('/solve', async (req, res) => {
  try {
    const { prompt, requestId } = req.body;
    
    if (!prompt) {
      return res.status(400).json({ 
        error: 'Prompt is required',
        requestId 
      });
    }

    console.log(`[${requestId || 'unknown'}] Processing BBH question...`);
    
    // Generate response using Mastra agent
    const response = await agent.generate(prompt, {
      maxTokens: 2000,
      temperature: 0.1  // Low temperature for consistent reasoning
    });
    
    const answer = response.text;
    console.log(`[${requestId || 'unknown'}] Generated response (${answer.length} chars)`);
    
    res.json({
      success: true,
      answer: answer,
      requestId: requestId,
      model: process.env.BBH_MODEL || 'gpt-4.1-nano',
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('Error processing BBH request:', error);
    
    res.status(500).json({
      success: false,
      error: error.message,
      requestId: req.body?.requestId,
      timestamp: new Date().toISOString()
    });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  console.error('Unhandled error:', error);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    timestamp: new Date().toISOString()
  });
});

// Start server
const PORT = process.env.MASTRA_PORT || 3000;
const server = app.listen(PORT, '127.0.0.1', () => {
  console.log(`Mastra BBH Server running on http://127.0.0.1:${PORT}`);
  console.log(`Model: ${process.env.BBH_MODEL || 'gpt-4.1-nano'}`);
  console.log('Ready to process BBH reasoning tasks...');
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Received SIGTERM, shutting down gracefully...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('Received SIGINT, shutting down gracefully...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

export default app;