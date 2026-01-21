#!/usr/bin/env node

/**
 * Schema-MCP Server
 *
 * Model Context Protocol server for JSON schema validation.
 * Provides schema validation tools to LLMs via MCP protocol.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  Tool,
  Resource,
} from "@modelcontextprotocol/sdk/types.js";
import Ajv from "ajv";
import addFormats from "ajv-formats";
import * as fs from "fs/promises";
import * as path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to schemas
const PROJECT_ROOT = path.join(__dirname, "..", "..", "..");
const SCHEMAS_DIR = path.join(PROJECT_ROOT, "config", "schemas");

// Initialize AJV validator
const ajv = new Ajv({ allErrors: true, verbose: true });
addFormats(ajv);

/**
 * Load JSON schema from file
 */
async function loadSchema(schemaName: string): Promise<any> {
  const schemaPath = path.join(SCHEMAS_DIR, schemaName);
  const content = await fs.readFile(schemaPath, "utf-8");
  return JSON.parse(content);
}

/**
 * Load JSON data from file
 */
async function loadJson(filePath: string): Promise<any> {
  const content = await fs.readFile(filePath, "utf-8");
  return JSON.parse(content);
}

/**
 * MCP Tools Definition
 */
const tools: Tool[] = [
  {
    name: "validate_json",
    description:
      "Validate a JSON file against a schema. Returns validation result with detailed error messages if validation fails.",
    inputSchema: {
      type: "object",
      properties: {
        json_path: {
          type: "string",
          description: "Path to JSON file to validate",
        },
        schema_name: {
          type: "string",
          description:
            'Schema name (e.g., "design_spec.schema.json"). Defaults to design_spec.schema.json',
          default: "design_spec.schema.json",
        },
      },
      required: ["json_path"],
    },
  },
  {
    name: "get_schema_info",
    description:
      "Get information about a schema including its structure, required fields, and field descriptions.",
    inputSchema: {
      type: "object",
      properties: {
        schema_name: {
          type: "string",
          description:
            'Schema name (e.g., "design_spec.schema.json"). Defaults to design_spec.schema.json',
          default: "design_spec.schema.json",
        },
      },
    },
  },
  {
    name: "generate_example",
    description:
      "Generate an example JSON that conforms to the schema. Useful for understanding schema structure.",
    inputSchema: {
      type: "object",
      properties: {
        schema_name: {
          type: "string",
          description:
            'Schema name (e.g., "design_spec.schema.json"). Defaults to design_spec.schema.json',
          default: "design_spec.schema.json",
        },
        minimal: {
          type: "boolean",
          description:
            "Generate minimal example (only required fields). Default: false",
          default: false,
        },
      },
    },
  },
  {
    name: "compare_schemas",
    description:
      "Compare two schemas and report differences. Useful for schema migration or compatibility checking.",
    inputSchema: {
      type: "object",
      properties: {
        schema1_name: {
          type: "string",
          description: "First schema name",
        },
        schema2_name: {
          type: "string",
          description: "Second schema name",
        },
      },
      required: ["schema1_name", "schema2_name"],
    },
  },
];

/**
 * MCP Resources Definition
 */
const resources: Resource[] = [
  {
    uri: "schema://design_spec",
    name: "DesignSpec Schema",
    description: "JSON schema for architectural design specifications",
    mimeType: "application/json",
  },
];

/**
 * Initialize MCP Server
 */
const server = new Server(
  {
    name: "schema-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
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
 * List available resources
 */
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources,
  };
});

/**
 * Read resource content
 */
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const { uri } = request.params;

  if (uri === "schema://design_spec") {
    const schema = await loadSchema("design_spec.schema.json");
    return {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify(schema, null, 2),
        },
      ],
    };
  }

  throw new Error(`Unknown resource: ${uri}`);
});

/**
 * Handle tool execution
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "validate_json":
        return await handleValidateJson(args);

      case "get_schema_info":
        return await handleGetSchemaInfo(args);

      case "generate_example":
        return await handleGenerateExample(args);

      case "compare_schemas":
        return await handleCompareSchemas(args);

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

async function handleValidateJson(args: any) {
  const { json_path, schema_name = "design_spec.schema.json" } = args;

  if (!json_path) {
    throw new Error("json_path is required");
  }

  // Load schema and data
  const schema = await loadSchema(schema_name);
  const data = await loadJson(json_path);

  // Validate
  const validate = ajv.compile(schema);
  const valid = validate(data);

  if (valid) {
    return {
      content: [
        {
          type: "text",
          text: `✓ Validation successful!\n\nFile: ${json_path}\nSchema: ${schema_name}\n\nThe JSON file conforms to the schema.`,
        },
      ],
    };
  } else {
    const errors = validate.errors || [];
    const errorMessages = errors.map((err) => {
      const path = err.instancePath || "/";
      const message = err.message || "unknown error";
      return `  - ${path}: ${message}`;
    });

    return {
      content: [
        {
          type: "text",
          text: `✗ Validation failed!\n\nFile: ${json_path}\nSchema: ${schema_name}\n\nErrors:\n${errorMessages.join("\n")}`,
        },
      ],
    };
  }
}

async function handleGetSchemaInfo(args: any) {
  const { schema_name = "design_spec.schema.json" } = args;

  const schema = await loadSchema(schema_name);

  // Extract info
  const info = {
    title: schema.title || schema_name,
    description: schema.description || "No description",
    type: schema.type,
    required: schema.required || [],
    properties: Object.keys(schema.properties || {}),
  };

  // Format output
  let output = `Schema Information: ${info.title}\n\n`;
  output += `Description: ${info.description}\n\n`;
  output += `Type: ${info.type}\n\n`;

  if (info.required.length > 0) {
    output += `Required Fields:\n`;
    info.required.forEach((field: string) => {
      output += `  - ${field}\n`;
    });
    output += `\n`;
  }

  if (info.properties.length > 0) {
    output += `Available Properties:\n`;
    info.properties.forEach((prop: string) => {
      const propSchema = schema.properties[prop];
      const desc = propSchema.description || "No description";
      output += `  - ${prop}: ${desc}\n`;
    });
  }

  return {
    content: [
      {
        type: "text",
        text: output,
      },
    ],
  };
}

async function handleGenerateExample(args: any) {
  const { schema_name = "design_spec.schema.json", minimal = false } = args;

  const schema = await loadSchema(schema_name);

  // Generate example based on schema
  const example = generateExampleFromSchema(schema, minimal);

  return {
    content: [
      {
        type: "text",
        text: `Example JSON for ${schema_name}:\n\n${JSON.stringify(example, null, 2)}`,
      },
    ],
  };
}

async function handleCompareSchemas(args: any) {
  const { schema1_name, schema2_name } = args;

  if (!schema1_name || !schema2_name) {
    throw new Error("Both schema1_name and schema2_name are required");
  }

  const schema1 = await loadSchema(schema1_name);
  const schema2 = await loadSchema(schema2_name);

  // Simple comparison
  const props1 = Object.keys(schema1.properties || {});
  const props2 = Object.keys(schema2.properties || {});

  const onlyIn1 = props1.filter((p) => !props2.includes(p));
  const onlyIn2 = props2.filter((p) => !props1.includes(p));
  const common = props1.filter((p) => props2.includes(p));

  let output = `Schema Comparison\n\n`;
  output += `Schema 1: ${schema1_name}\n`;
  output += `Schema 2: ${schema2_name}\n\n`;

  output += `Common properties: ${common.length}\n`;
  if (common.length > 0) {
    common.forEach((p) => {
      output += `  - ${p}\n`;
    });
  }
  output += `\n`;

  output += `Only in ${schema1_name}: ${onlyIn1.length}\n`;
  if (onlyIn1.length > 0) {
    onlyIn1.forEach((p) => {
      output += `  - ${p}\n`;
    });
  }
  output += `\n`;

  output += `Only in ${schema2_name}: ${onlyIn2.length}\n`;
  if (onlyIn2.length > 0) {
    onlyIn2.forEach((p) => {
      output += `  - ${p}\n`;
    });
  }

  return {
    content: [
      {
        type: "text",
        text: output,
      },
    ],
  };
}

/**
 * Generate example JSON from schema
 */
function generateExampleFromSchema(schema: any, minimal: boolean): any {
  if (schema.type === "object") {
    const result: any = {};
    const props = schema.properties || {};
    const required = schema.required || [];

    for (const [key, propSchema] of Object.entries(props)) {
      if (minimal && !required.includes(key)) {
        continue;
      }
      result[key] = generateExampleValue(propSchema as any);
    }

    return result;
  } else if (schema.type === "array") {
    return [generateExampleValue(schema.items)];
  } else {
    return generateExampleValue(schema);
  }
}

function generateExampleValue(schema: any): any {
  if (schema.example !== undefined) {
    return schema.example;
  }

  switch (schema.type) {
    case "string":
      return schema.enum ? schema.enum[0] : "example";
    case "number":
    case "integer":
      return 0;
    case "boolean":
      return false;
    case "array":
      return [];
    case "object":
      return generateExampleFromSchema(schema, false);
    default:
      return null;
  }
}

/**
 * Start server
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("Schema-MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
