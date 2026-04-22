# Expected: Skill Create Flow

## 預期產出

### 目錄結構
```
skills/test-demo-skill/
├── SKILL.md          # 必須包含 YAML frontmatter
└── README.md         # 選用但建議
```

### SKILL.md 預期內容
```yaml
---
name: test-demo-skill
description: Integration test demo skill
version: 1.0.0
allowed-tools:
  - Read
  - Write
  - Bash
---
```

### 關鍵驗證點
1. SKILL.md 存在且有正確的 YAML frontmatter
2. name 欄位使用 kebab-case
3. allowed-tools 有列出正確的工具
4. 目錄名稱與 skill name 一致
