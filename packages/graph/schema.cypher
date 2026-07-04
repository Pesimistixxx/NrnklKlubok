// ============================================================
//  MKG — схема Neo4j: constraints и indexes для 6 слоёв графа
//  Идемпотентно (IF NOT EXISTS). Запуск: mkg-graph init-schema
// ============================================================

// ── L1: Онтологическое ядро ─────────────────────────────────
CREATE CONSTRAINT material_id       IF NOT EXISTS FOR (n:Material)        REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT process_id        IF NOT EXISTS FOR (n:Process)         REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT equipment_id      IF NOT EXISTS FOR (n:Equipment)       REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT reagent_id        IF NOT EXISTS FOR (n:ChemicalReagent) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT stdmetric_id      IF NOT EXISTS FOR (n:StandardMetric)  REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT phase_id          IF NOT EXISTS FOR (n:PhaseState)      REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT property_id       IF NOT EXISTS FOR (n:Property)        REQUIRE n.id IS UNIQUE;

// ── L2: Документы и контекст ────────────────────────────────
CREATE CONSTRAINT document_id       IF NOT EXISTS FOR (n:Document)        REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT expert_id         IF NOT EXISTS FOR (n:Expert)          REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT location_id       IF NOT EXISTS FOR (n:Location)        REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT organization_id   IF NOT EXISTS FOR (n:Organization)    REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT event_id          IF NOT EXISTS FOR (n:Event)           REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT timeline_id       IF NOT EXISTS FOR (n:Timeline)        REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT facility_id       IF NOT EXISTS FOR (n:Facility)        REQUIRE n.id IS UNIQUE;

// ── L3: Текстовая матрица ───────────────────────────────────
CREATE CONSTRAINT paragraph_id      IF NOT EXISTS FOR (n:TextParagraph)   REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT table_id          IF NOT EXISTS FOR (n:TableMatrix)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT heading_id        IF NOT EXISTS FOR (n:HeadingContext)  REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT lang_id           IF NOT EXISTS FOR (n:LangContext)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT synonym_id        IF NOT EXISTS FOR (n:SynonymMap)      REQUIRE n.id IS UNIQUE;

// ── L4: Факты и телеметрия ──────────────────────────────────
CREATE CONSTRAINT run_id            IF NOT EXISTS FOR (n:ExperimentRun)   REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT stage_id          IF NOT EXISTS FOR (n:TechStage)       REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT measurement_id    IF NOT EXISTS FOR (n:Measurement)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT deviation_id      IF NOT EXISTS FOR (n:Deviation)       REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT trend_id          IF NOT EXISTS FOR (n:TrendVector)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT formula_id        IF NOT EXISTS FOR (n:Formula)         REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT envcond_id        IF NOT EXISTS FOR (n:EnvironmentalCondition) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT effect_id         IF NOT EXISTS FOR (n:Effect)          REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT claim_id          IF NOT EXISTS FOR (n:Claim)           REQUIRE n.id IS UNIQUE;

// ── L5: Валидация и безопасность ────────────────────────────
CREATE CONSTRAINT verification_id   IF NOT EXISTS FOR (n:VerificationStatus) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT securityrole_id   IF NOT EXISTS FOR (n:SecurityRole)    REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT contradiction_id  IF NOT EXISTS FOR (n:Contradiction)   REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT audit_id          IF NOT EXISTS FOR (n:AuditTrail)      REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT gap_id            IF NOT EXISTS FOR (n:KnowledgeGap)    REQUIRE n.id IS UNIQUE;

// ── L6: Экономика и экология ────────────────────────────────
CREATE CONSTRAINT solution_id       IF NOT EXISTS FOR (n:TechnologySolution)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT econ_id           IF NOT EXISTS FOR (n:EconomicIndicator)      REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT envind_id         IF NOT EXISTS FOR (n:EnvironmentalIndicator) REQUIRE n.id IS UNIQUE;

// ── Индексы для поиска/нормализации ─────────────────────────
CREATE INDEX material_name_en   IF NOT EXISTS FOR (n:Material) ON (n.name_en);
CREATE INDEX material_name_ru   IF NOT EXISTS FOR (n:Material) ON (n.name_ru);
CREATE INDEX process_name_en    IF NOT EXISTS FOR (n:Process)  ON (n.name_en);
CREATE INDEX document_hash      IF NOT EXISTS FOR (n:Document)  ON (n.hash_sum);
CREATE INDEX contradiction_status IF NOT EXISTS FOR (n:Contradiction) ON (n.status);
CREATE INDEX claim_predicate    IF NOT EXISTS FOR (n:Claim)     ON (n.predicate);
CREATE INDEX measurement_param  IF NOT EXISTS FOR (n:Measurement) ON (n.parameter);

// Полнотекстовый индекс по алиасам онтологии (entity resolution)
CREATE FULLTEXT INDEX ontology_aliases IF NOT EXISTS
FOR (n:Material|Process|Equipment|ChemicalReagent)
ON EACH [n.name_ru, n.name_en, n.aliases];
