# LLM-CAD Integration System - Context Document

**For Claude Code: Read this document first when starting a new conversation about this project.**

Last Updated: 2025-01-20 22:00 KST

---

## Project Overview

### What is this project?
**LLM-CAD Integration System (A-ADS - Autonomous Architectural Design System)**

설계 기획문서(JSON)와 기존 CAD 도면을 입력받아, 기획에 적합한 새로운 CAD 도면을 자동으로 생성하는 워크플로우 시스템입니다.

### Current Status: **Phase 1 MVP - COMPLETED ✅**

---

## System Architecture

```
사용자 (Human Architect)
    ↓ [자연어 또는 구조화된 JSON 입력]
Orchestrator Agent (수석 설계 에이전트) - Phase 2
    - LLM: Claude 3.5 Sonnet
    - 역할: JSON 스펙 생성 및 작업 조율
    - 산출물: DesignSpec JSON (Single Source of Truth)
    ↓
MCP Server Layer (Model Context Protocol) - Phase 2
    - CAD-MCP Server: DXF/DWG 처리
    - Schema-MCP Server: JSON 검증
    - Revit-MCP Server: BIM 모델링
    - Compliance-MCP Server: 법규 검증
    ↓
Implementation Agents (CAD 구현 에이전트들)
    ✅ AutoCAD Agent: ezdxf로 2D 도면 생성 (MVP 완료)
    ⏳ Revit Agent: pyRevit/ifcopenshell로 BIM 생성 (Phase 2)
    ⏳ Rhino Agent: rhino3dm으로 파라메트릭 디자인 (Phase 2)
```

---

## Technical Stack

### Core Technologies
- **Python 3.10+**: Main programming language
- **ezdxf 1.4.3**: DXF file generation (no AutoCAD required)
- **Pydantic 2.12.5**: Data validation and modeling
- **Shapely 2.1.2**: 2D geometry operations
- **Anthropic Claude API**: LLM integration (Phase 2)

### Development Environment
- **Virtual Environment**: `venv/` (activated via `venv/Scripts/activate`)
- **Package Manager**: pip
- **Testing**: pytest
- **Code Quality**: black (formatter), mypy (type checker)

### Phase 2 Technologies (준비 완료)
- **Node.js 18+**: MCP servers (TypeScript)
- **@modelcontextprotocol/sdk**: MCP protocol implementation
- **FastAPI**: REST API (optional)

---

## Project Structure

```
llm-cad-integration/
├── venv/                           # Python virtual environment ✅
│
├── config/
│   ├── schemas/
│   │   └── design_spec.schema.json # JSON schema definition
│   ├── templates/
│   │   └── autocad/                # DXF templates
│   └── settings.yaml               # System configuration
│
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── design_spec.py          # Pydantic models
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── dxf_generator.py        # ✅ DXF generation engine
│   │   ├── schema_validator.py     # ✅ JSON schema validation
│   │   └── geometry_engine.py      # ✅ Geometric calculations
│   ├── agents/
│   │   ├── __init__.py
│   │   └── autocad_agent.py        # ✅ AutoCAD agent
│   ├── orchestrator/               # ⏳ Phase 2
│   ├── core/                       # ⏳ Phase 2
│   └── utils/
│
├── mcp-servers/                    # ⏳ Phase 2
│   ├── cad-mcp/
│   │   ├── package.json            # ✅ MCP server config
│   │   ├── tsconfig.json
│   │   ├── src/
│   │   │   └── index.ts
│   │   └── scripts/
│   │       └── create_floor_plan.py
│   └── schema-mcp/
│       └── ...
│
├── tests/
│   ├── fixtures/
│   │   ├── 3ldk_apartment.json     # ✅ Sample: 3LDK apartment
│   │   └── simple_room.json        # ✅ Sample: Simple room
│   ├── unit/
│   └── integration/
│
├── examples/
│   └── simple_test.py              # ✅ Quick test script
│
├── output/                         # Generated DXF files
│
├── .env.example                    # Environment variables template
├── .gitignore
├── requirements.txt                # Python dependencies
├── README.md                       # User documentation
├── CONTEXT.md                      # THIS FILE
└── PROJECT_STATUS.md               # Current implementation status
```

---

## Key Concepts

### 1. Single Source of Truth: DesignSpec JSON

모든 설계 정보는 구조화된 JSON 스펙으로 관리됩니다.

**Schema Location**: `config/schemas/design_spec.schema.json`

**Example Structure**:
```json
{
  "project_info": {
    "name": "프로젝트명",
    "client": "클라이언트명"
  },
  "building": {
    "floors": [
      {
        "level": 1,
        "rooms": [
          {
            "name": "거실",
            "type": "living_room",
            "geometry": {
              "type": "Polygon",
              "coordinates": [[0,0], [6,0], [6,4], [0,4], [0,0]]
            },
            "doors": [...],
            "windows": [...],
            "furniture": [...]
          }
        ]
      }
    ]
  }
}
```

### 2. Key Design Principles

1. **구조화된 계약 패러다임**: AI의 창의성보다 신뢰성에 중점
2. **에이전트 분업화**: "기획"과 "실행"의 분리로 오류 방지
3. **로컬 실행 우선**: AutoCAD 설치 불필요 (ezdxf 사용)
4. **개방형 표준 기반**: JSON Schema, DXF, IFC 등
5. **확장 가능한 아키텍처**: MCP 프로토콜 기반

### 3. Coordinate System

- **Units**: Meters (미터)
- **Origin**: (0, 0) is bottom-left
- **Coordinates**: [x, y] format
- **Polygons**: Must be closed (first point == last point)

### 4. Wall Indexing

```
Room Polygon: [(0,0), (5,0), (5,4), (0,4), (0,0)]

Wall indices:
  wall_index 0: (0,0) → (5,0)  (bottom)
  wall_index 1: (5,0) → (5,4)  (right)
  wall_index 2: (5,4) → (0,4)  (top)
  wall_index 3: (0,4) → (0,0)  (left)
```

---

## Common Commands

### Activate Virtual Environment
```bash
# Windows
cd "C:\Users\user1\Desktop\CAD LLM  연동리서치\llm-cad-integration"
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Run Simple Test
```bash
python examples/simple_test.py
```

### Generate Floor Plan from JSON
```python
from pathlib import Path
from src.agents import AutoCADAgent

schema_path = Path("config/schemas/design_spec.schema.json")
agent = AutoCADAgent(schema_path=schema_path)

agent.create_floor_plan_from_json(
    json_path=Path("tests/fixtures/3ldk_apartment.json"),
    output_path=Path("output/my_floor_plan.dxf"),
    floor_level=1
)
```

### Install New Dependencies
```bash
venv\Scripts\pip install package-name
# Then update requirements.txt:
venv\Scripts\pip freeze > requirements.txt
```

### Run Tests (when implemented)
```bash
pytest tests/unit/
pytest tests/integration/
pytest --cov=src tests/
```

---

## Implementation History

### Session 1: 2025-01-20 (Initial Development)

**Completed**:
1. ✅ Project structure setup
2. ✅ JSON schema definition (`design_spec.schema.json`)
3. ✅ Pydantic data models (`models/design_spec.py`)
4. ✅ DXF Generator skill (`skills/dxf_generator.py`)
   - Wall creation with thickness
   - Door and window placement
   - Furniture layout
   - Room labeling
   - Layer management (WALL, DOOR, WINDOW, FURNITURE, DIMENSION, TEXT)
5. ✅ Schema Validator (`skills/schema_validator.py`)
6. ✅ Geometry Engine (`skills/geometry_engine.py`)
7. ✅ AutoCAD Agent (`agents/autocad_agent.py`)
8. ✅ Sample test data (3LDK apartment, simple room)
9. ✅ Virtual environment setup and dependencies installation
10. ✅ Documentation (README.md, CONTEXT.md, PROJECT_STATUS.md)

**Key Files Created**:
- `config/schemas/design_spec.schema.json` (672 lines)
- `src/models/design_spec.py` (284 lines)
- `src/skills/dxf_generator.py` (377 lines)
- `src/agents/autocad_agent.py` (156 lines)
- `tests/fixtures/3ldk_apartment.json` (완전한 3LDK 예제)
- `examples/simple_test.py` (실행 가능한 데모)

---

## Known Issues & Limitations (MVP)

### Current Limitations
1. **2D Only**: No 3D modeling support yet
2. **Single Floor per File**: Cannot generate multi-story in one DXF
3. **No Structural Analysis**: Pure geometric generation
4. **No MEP Systems**: No mechanical/electrical/plumbing
5. **No Building Code Compliance**: Validation not yet implemented (Phase 3)

### Technical Debt
- [ ] No unit tests yet (test files created but empty)
- [ ] No integration tests
- [ ] Orchestrator Agent not implemented (Phase 2)
- [ ] MCP servers prepared but not implemented (Phase 2)
- [ ] No CLI tool (currently library-only)

---

## Next Steps (Phase 2)

### Priority 1: Testing
- [ ] Write unit tests for DXFGenerator
- [ ] Write unit tests for Schema Validator
- [ ] Write integration test for end-to-end workflow
- [ ] Add pytest fixtures

### Priority 2: MCP Server Implementation
- [ ] Implement CAD-MCP Server (TypeScript)
- [ ] Implement Schema-MCP Server
- [ ] Test MCP communication

### Priority 3: Orchestrator Agent
- [ ] Integrate Claude API
- [ ] Natural language → JSON spec conversion
- [ ] Task distribution logic
- [ ] Multi-agent coordination

### Priority 4: Additional Agents
- [ ] Revit Agent (IFC file generation)
- [ ] Rhino Agent (3dm file generation)
- [ ] Site Analysis Agent
- [ ] Structural Design Agent

---

## Research Context

### Referenced Documents (in parent directory)

이 프로젝트는 다음 연구 문서들의 아이디어를 기반으로 구현되었습니다:

1. **1.1-1.4**: LLM 주도형 자율 건축 설계 시스템 (A-ADS) 아키텍처
2. **2.1-2.3**: LLM-CAD 통합 보고서
3. **3.1-3.2**: LLM과 CAD 통합 워크플로우 혁신 방안

**핵심 아이디어**:
- 모호성 비용(Ambiguity Tax)에서 구조화된 계약으로
- JSON 스키마 기반 99% 준수율 달성
- Orchestrator + Implementation Agents 아키텍처
- MCP(Model Context Protocol) 통합
- 로컬 실행 우선 (데이터 보안)

---

## Important Notes for Future Sessions

### When Resuming Work

1. **Always check `PROJECT_STATUS.md`** for current implementation status
2. **Review recent changes** in git log (if using git)
3. **Activate virtual environment** before any Python work
4. **Check `.env` file** exists (copy from `.env.example` if needed)
5. **Run simple test** to verify system works: `python examples/simple_test.py`

### When Adding Features

1. **Update JSON schema** if adding new data fields
2. **Update Pydantic models** to match schema
3. **Write tests** for new functionality
4. **Update PROJECT_STATUS.md** with progress
5. **Update this CONTEXT.md** if architecture changes

### When Debugging

1. Check validation errors: Schema → Model → Geometry
2. Verify polygon coordinates are closed
3. Check door/window wall_index is valid
4. Ensure all coordinates are numeric (not string)
5. Use `agent.analyze_floor_plan()` to inspect spec

---

## Contact & Resources

### Documentation
- **README.md**: User-facing documentation
- **CONTEXT.md**: This file (for Claude Code)
- **PROJECT_STATUS.md**: Detailed implementation tracking
- **config/schemas/design_spec.schema.json**: JSON schema reference

### External Resources
- ezdxf docs: https://ezdxf.readthedocs.io/
- Pydantic docs: https://docs.pydantic.dev/
- Shapely docs: https://shapely.readthedocs.io/
- MCP SDK: https://github.com/modelcontextprotocol/sdk
- Anthropic Claude: https://docs.anthropic.com/

---

## Quick Reference: File Locations

**Most Important Files**:
- JSON Schema: `config/schemas/design_spec.schema.json`
- Pydantic Models: `src/models/design_spec.py`
- DXF Generator: `src/skills/dxf_generator.py`
- AutoCAD Agent: `src/agents/autocad_agent.py`
- Sample Data: `tests/fixtures/3ldk_apartment.json`
- Test Script: `examples/simple_test.py`

**Configuration**:
- Settings: `config/settings.yaml`
- Dependencies: `requirements.txt`
- Environment: `.env` (create from `.env.example`)

**Status Tracking**:
- This context: `CONTEXT.md`
- Project status: `PROJECT_STATUS.md`
- User docs: `README.md`
- Claude Code guide: `../CLAUDE.md` (parent directory)

---

**End of Context Document**

*This document should be read at the start of every new conversation about this project to provide full context.*
