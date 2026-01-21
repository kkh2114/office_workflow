#!/usr/bin/env node

/**
 * CAD-MCP Server
 *
 * Model Context Protocol server for CAD file generation.
 * Exposes DXF generation tools to LLMs via MCP protocol.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import { promisify } from "util";
import * as fs from "fs/promises";
import * as path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to Python scripts
const PYTHON_SCRIPTS_DIR = path.join(__dirname, "..", "scripts");
const PROJECT_ROOT = path.join(__dirname, "..", "..", "..");
const VENV_PYTHON = path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe");

/**
 * Execute Python script with arguments
 */
async function executePython(
  scriptName: string,
  args: string[] = []
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(PYTHON_SCRIPTS_DIR, scriptName);
    const pythonExe = VENV_PYTHON;

    const process = spawn(pythonExe, [scriptPath, ...args]);

    let stdout = "";
    let stderr = "";

    process.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    process.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    process.on("close", (code) => {
      resolve({
        stdout,
        stderr,
        exitCode: code || 0,
      });
    });

    process.on("error", (error) => {
      reject(error);
    });
  });
}

/**
 * MCP Tools Definition
 */
const tools: Tool[] = [
  {
    name: "create_floor_plan",
    description:
      "Generate a DXF floor plan from a DesignSpec JSON. Creates 2D CAD drawing with walls, doors, windows, and furniture.",
    inputSchema: {
      type: "object",
      properties: {
        json_path: {
          type: "string",
          description: "Path to DesignSpec JSON file",
        },
        output_path: {
          type: "string",
          description: "Path for output DXF file",
        },
        floor_level: {
          type: "number",
          description: "Floor level to generate (default: 1)",
          default: 1,
        },
      },
      required: ["json_path", "output_path"],
    },
  },
  {
    name: "validate_design_spec",
    description:
      "Validate a DesignSpec JSON against the schema. Checks structure, data types, and geometric validity.",
    inputSchema: {
      type: "object",
      properties: {
        json_path: {
          type: "string",
          description: "Path to DesignSpec JSON file to validate",
        },
      },
      required: ["json_path"],
    },
  },
  {
    name: "analyze_floor_plan",
    description:
      "Analyze a floor plan from DesignSpec JSON. Returns room areas, perimeters, and statistics.",
    inputSchema: {
      type: "object",
      properties: {
        json_path: {
          type: "string",
          description: "Path to DesignSpec JSON file",
        },
        floor_level: {
          type: "number",
          description: "Floor level to analyze (default: 1)",
          default: 1,
        },
      },
      required: ["json_path"],
    },
  },
  {
    name: "convert_spec_format",
    description:
      "Convert DesignSpec between different formats (JSON <-> YAML, pretty-print, minify)",
    inputSchema: {
      type: "object",
      properties: {
        input_path: {
          type: "string",
          description: "Path to input file",
        },
        output_path: {
          type: "string",
          description: "Path for output file",
        },
        format: {
          type: "string",
          enum: ["json", "yaml", "json-pretty", "json-minified"],
          description: "Target format",
        },
      },
      required: ["input_path", "output_path", "format"],
    },
  },
];

/**
 * Initialize MCP Server
 */
const server = new Server(
  {
    name: "cad-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * List available tools
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools,
  };
});

/**
 * Handle tool execution
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "create_floor_plan":
        return await handleCreateFloorPlan(args);

      case "validate_design_spec":
        return await handleValidateSpec(args);

      case "analyze_floor_plan":
        return await handleAnalyzeFloorPlan(args);

      case "convert_spec_format":
        return await handleConvertFormat(args);

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [
        {
          type: "text",
          text: `Error: ${errorMessage}`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Tool Handlers
 */

async function handleCreateFloorPlan(args: any) {
  const { json_path, output_path, floor_level = 1 } = args;

  // Validate inputs
  if (!json_path || !output_path) {
    throw new Error("json_path and output_path are required");
  }

  // Execute Python script
  const result = await executePython("create_floor_plan.py", [
    json_path,
    output_path,
    String(floor_level),
  ]);

  if (result.exitCode !== 0) {
    throw new Error(`Floor plan generation failed: ${result.stderr}`);
  }

  return {
    content: [
      {
        type: "text",
        text: `Floor plan generated successfully!\n\nOutput: ${output_path}\n\n${result.stdout}`,
      },
    ],
  };
}

async function handleValidateSpec(args: any) {
  const { json_path } = args;

  if (!json_path) {
    throw new Error("json_path is required");
  }

  const result = await executePython("validate_spec.py", [json_path]);

  return {
    content: [
      {
        type: "text",
        text: result.stdout || result.stderr,
      },
    ],
  };
}

async function handleAnalyzeFloorPlan(args: any) {
  const { json_path, floor_level = 1 } = args;

  if (!json_path) {
    throw new Error("json_path is required");
  }

  const result = await executePython("analyze_floor_plan.py", [
    json_path,
    String(floor_level),
  ]);

  if (result.exitCode !== 0) {
    throw new Error(`Analysis failed: ${result.stderr}`);
  }

  return {
    content: [
      {
        type: "text",
        text: result.stdout,
      },
    ],
  };
}

async function handleConvertFormat(args: any) {
  const { input_path, output_path, format } = args;

  if (!input_path || !output_path || !format) {
    throw new Error("input_path, output_path, and format are required");
  }

  const result = await executePython("convert_format.py", [
    input_path,
    output_path,
    format,
  ]);

  if (result.exitCode !== 0) {
    throw new Error(`Conversion failed: ${result.stderr}`);
  }

  return {
    content: [
      {
        type: "text",
        text: `Format conversion successful!\n\nOutput: ${output_path}\n\n${result.stdout}`,
      },
    ],
  };
}

/**
 * Start server
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("CAD-MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
