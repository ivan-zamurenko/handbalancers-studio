# Skills: минимум, который действительно нужен

В kit включён один **проектный**, а не официальный OpenAI-certified skill: `studio-task-delivery`. Он реализует твой конкретный процесс task → test-first → bounded change → evidence. Создан через skill-creator; структура проверяется его валидатором. Это не гарантия качества произвольного будущего кода.

Для Codex repository path `.agents/skills/studio-task-delivery`. Для отдельной установки выдан `skill.zip` с одним skill. Не устанавливать обе копии в несколько scopes под одним именем без необходимости. Инструкции и scripts сторонних skills сначала прочитать; не устанавливать случайный «ultimate best practices pack».

Дополнительный skill подключать по реальной задаче: Figma design-to-code при переносе конкретного Figma frame; migration workflow при изменении DDL; Playwright/browser workflow при взаимодействии с UI; security review при auth/RLS/payment. Проверить, что он действительно доступен и его trigger узкий. Если нет — использовать первичные docs и project tests, а не утверждать, что skill применён.

Не загружать все skills на каждый task. Не добавлять архитектурные предписания, конфликтующие с согласованным monolith/vanilla stack. Root AGENTS остаётся коротким; подробные контракты в docs читаются по необходимости. Это согласуется с официальной рекомендацией OpenAI о узких triggers и progressive disclosure [S-SKILLBLOG][S-SKILLS].
