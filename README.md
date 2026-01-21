# LLM-CAD Integration System

**Autonomous Architectural Design System (A-ADS)** - Phase 2+ Complete ✅

LLM-CAD 통합 시스템은 자연어 또는 JSON 기획문서를 입력받아 완전한 건축 설계 도면과 분석 보고서를 자동으로 생성하는 통합 워크플로우 시스템입니다.

## Features (Complete)

### Phase 1: Core CAD Generation ✅
- **JSON 기반 설계 스펙**: 구조화된 JSON 스키마로 모든 설계 정보 관리
- **AutoCAD DXF 생성**: ezdxf 라이브러리 사용 (AutoCAD 설치 불필요)
- **자동 평면도 생성**: 벽, 문, 창문, 가구 자동 배치
- **데이터 검증**: JSON 스키마 기반 엄격한 검증

### Phase 2: Multi-Agent System ✅
- **Orchestrator Agent**: Claude API 통합, 자연어 → JSON 변환, 대화 관리
- **CAD-MCP Server**: DXF 생성 도구를 MCP 프로토콜로 노출
- **Schema-MCP Server**: JSON 스키마 검증 도구 제공
- **Revit Agent**: IFC (BIM) 파일 생성
- **Rhino Agent**: 3D 파라메트릭 모델 (.3dm) 생성

### Phase 3: Analysis & Design ✅
- **Site Analysis Agent**: 대지 분석, 일조권 계산, 그림자 분석
- **Structural Agent**: 구조 설계, 하중 계산, 기둥/보 설계
- **MEP Agent**: 설비 시스템 (기계/전기/배관) 설계
- **Compliance Agent**: 건축법규 검증 (용적률/건폐율/주차대수 등)

## System Requirements

- Python 3.10 이상
- Node.js 18 이상 (MCP 서버용)
- 8GB RAM (권장 16GB)
- Windows 10/11 또는 Linux

**AutoCAD 설치 불필요** - ezdxf 라이브러리를 사용하여 독립적으로 DXF 파일 생성

## Installation

### 1. Clone Repository

```bash
cd "C:\Users\user1\Desktop\CAD LLM  연동리서치\llm-cad-integration"
```

### 2. Python Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy environment template
copy .env.example .env

# Edit .env and add your API keys
# ANTHROPIC_API_KEY=your-key-here
```

## Quick Start

### Generate Floor Plan from JSON

```python
from pathlib import Path
from src.models import DesignSpec
from src.agents import AutoCADAgent

# Load specification
spec_path = Path("tests/fixtures/3ldk_apartment.json")
output_path = Path("output/3ldk_floor_plan.dxf")

# Create AutoCAD agent
schema_path = Path("config/schemas/design_spec.schema.json")
agent = AutoCADAgent(schema_path=schema_path)

# Generate floor plan
agent.create_floor_plan_from_json(
    json_path=spec_path,
    output_path=output_path,
    floor_level=1
)

print(f"Floor plan generated: {output_path}")
```

### Run Simple Test

```bash
# Run the example script
python examples/simple_test.py
```

## Project Structure

```
llm-cad-integration/
├── config/
│   ├── schemas/              # JSON schemas
│   └── settings.yaml         # System configuration
├── src/
│   ├── agents/               # Implementation agents
│   │   └── autocad_agent.py  # AutoCAD agent
│   ├── skills/               # Functional modules
│   │   ├── dxf_generator.py  # DXF generation
│   │   ├── schema_validator.py
│   │   └── geometry_engine.py
│   └── models/               # Data models (Pydantic)
│       └── design_spec.py
├── mcp-servers/              # MCP servers (Phase 2)
├── tests/
│   └── fixtures/             # Sample JSON specs
└── output/                   # Generated DXF files
```

## JSON Specification Format

Design specifications follow the JSON schema defined in `config/schemas/design_spec.schema.json`.

### Example: Simple Room

```json
{
  "project_info": {
    "name": "Simple Room",
    "client": "Test Client"
  },
  "building": {
    "floors": [
      {
        "level": 1,
        "rooms": [
          {
            "name": "Living Room",
            "type": "living_room",
            "geometry": {
              "type": "Polygon",
              "coordinates": [[0, 0], [5, 0], [5, 4], [0, 4], [0, 0]]
            },
            "doors": [
              {"wall_index": 0, "position": 0.5, "width": 0.9}
            ],
            "windows": [
              {"wall_index": 2, "position": 0.5, "width": 1.5}
            ]
          }
        ]
      }
    ]
  }
}
```

### Key Concepts

- **geometry.coordinates**: Room boundary as polygon `[[x1, y1], [x2, y2], ...]`
- **wall_index**: Which wall segment (0-based) for doors/windows
- **position**: Position along wall (0.0 = start, 1.0 = end)
- All dimensions in meters

## Usage Examples

### Example 1: 3LDK Apartment

```bash
python examples/simple_test.py
```

Generates a complete 3LDK apartment floor plan with:
- 거실 (Living room) 20㎡
- 주방 (Kitchen) 10㎡
- 침실 2개 (2 Bedrooms) 12㎡, 10㎡
- 욕실 (Bathroom) 5㎡

Output: `output/3ldk_apartment.dxf`

### Example 2: Analyze Floor Plan

```python
from src.agents import AutoCADAgent
from src.models import DesignSpec
import json

# Load spec
with open("tests/fixtures/3ldk_apartment.json") as f:
    spec_dict = json.load(f)

spec = DesignSpec(**spec_dict)

# Analyze
agent = AutoCADAgent()
stats = agent.analyze_floor_plan(spec, floor_level=1)

print(f"Total Area: {stats['total_area']}㎡")
print(f"Number of Rooms: {stats['num_rooms']}")
for room in stats['rooms']:
    print(f"  - {room['name']}: {room['area']}㎡")
```

## Validation

The system performs comprehensive validation:

1. **JSON Schema Validation**: Ensures spec conforms to schema
2. **Model Validation**: Pydantic model validation
3. **Geometry Validation**: Checks for closed polygons, valid coordinates
4. **Logical Validation**: Door/window indices, wall segments

```python
from src.skills import DesignSpecValidator

validator = DesignSpecValidator(schema_path)
is_valid, errors = validator.full_validation(spec)

if not is_valid:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

## Testing

### Run Unit Tests

```bash
pytest tests/unit/
```

### Run Integration Tests

```bash
pytest tests/integration/
```

### Test Coverage

```bash
pytest --cov=src tests/
```

## Configuration

Edit `config/settings.yaml` to customize:

- Layer colors and names
- Default dimensions (wall thickness, door width, etc.)
- DXF version
- Logging settings

## Architecture

### Current (Phase 1 - MVP)

```
User
  ↓
AutoCAD Agent
  ├─ DXF Generator (ezdxf)
  ├─ Schema Validator
  └─ Geometry Engine
  ↓
DXF File
```

### Future (Phase 2+)

```
User
  ↓
Orchestrator Agent (Claude API)
  ↓
MCP Server Layer
  ├─ CAD-MCP Server
  ├─ Schema-MCP Server
  └─ Compliance-MCP Server
  ↓
Implementation Agents
  ├─ AutoCAD Agent
  ├─ Revit Agent
  └─ Rhino Agent
```

## Limitations (MVP)

- 2D floor plans only (no 3D)
- Single floor per file
- No structural analysis
- No MEP (Mechanical/Electrical/Plumbing) systems
- No building code compliance checking (Phase 3)

## Roadmap

### Phase 1: MVP ✅ (Current)
- [x] JSON schema definition
- [x] Pydantic models
- [x] DXF Generator
- [x] AutoCAD Agent
- [x] Basic validation

### Phase 2: Multi-CAD Support
- [ ] Revit Agent (IFC files)
- [ ] Rhino Agent (3dm files)
- [ ] MCP Server implementation
- [ ] Orchestrator Agent (Claude API)
- [ ] Multi-agent workflow

### Phase 3: Advanced Features
- [ ] Building code compliance checking
- [ ] QA automation
- [ ] Structural design agent
- [ ] MEP design agent
- [ ] Cost estimation

## Contributing

This is a research/prototype project. Contributions welcome!

## License

MIT License

## Support

For issues and questions, refer to the project documentation or contact the development team.

---

**Generated by LLM-CAD Integration System**
Built with Python, ezdxf, Pydantic, and Claude Code
