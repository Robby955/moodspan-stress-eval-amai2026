// Generation, grounding-contract, judge, and critique call sites, copied
// verbatim from scripts/eval-response-quality.ts:603-704. This is the block
// that fixes the decoding parameters the paper reports: generation at
// temperature 0.3 with a 2048-token cap, judge and critique at temperature 0.1
// with a 512-token cap, one call each per query.
//
// Nothing below is edited.

// ─── scripts/eval-response-quality.ts:603-704 ────────────────────────────────

      // ── Step 4: Build messages and call configured generation backend ──
      let userMessage = "";
      if (safety.level === "caution") {
        userMessage += buildCrisisResponse(safety) + "\n\n";
      }
      userMessage += `<context>\n${contextText}\n</context>\n\nUser question: ${entry.question}`;

      const genStart = Date.now();
      try {
        kiraResponse = await callBackend(
          config.generationBackend,
          [
            { role: "system", content: `${KIRA_SYSTEM_PROMPT}\n\n${CANONICAL_SAFETY_CONTEXT}` },
            { role: "user", content: userMessage },
          ],
          0.3,
          2048,
        );
      } catch (err) {
        kiraResponse = `[Generation error: ${err instanceof Error ? err.message : String(err)}]`;
      }
      generationLatency = Date.now() - genStart;

      const contractResult = applyEvalGroundingContract({
        responseText: kiraResponse,
        searchResults,
        queryText: entry.question,
      });
      kiraResponse = contractResult.finalText;
      groundingContract = summarizeEvalGroundingContract(contractResult, searchResults);

      // Rate limit delay
      await sleep(config.generationSleepMs);
    }

    // ── Step 5: LLM-as-Judge ──
    const judgeStart = Date.now();
    let judgeScores: JudgeScores;

    try {
      const isSafetyQuery = SAFETY_CATEGORIES.has(entry.category);
      const judgePrompt =
        isSafetyQuery && (safety.level !== "safe" || entry.category === "edge_case")
          ? buildSafetyJudgePrompt(
              entry,
              kiraResponse,
              safety.level,
              !guard.allowed,
            )
          : buildJudgePrompt(entry, contextText, kiraResponse);

      const judgeResponse = await callBackend(
        config.judgeBackend,
        [{ role: "user", content: judgePrompt }],
        0.1,
        512,
      );
      judgeScores = parseJudgeResponse(judgeResponse);
    } catch (err) {
      console.log(
        `   Judge failed for ${entry.id}: ${err instanceof Error ? err.message : String(err)}`,
      );
      judgeScores = {
        correctness: 3,
        completeness: 3,
        grounding: 3,
        safety_compliance: 3,
        hallucination_detected: false,
        hallucination_details: "",
        explanation: "Judge call failed",
      };
    }
    const judgeLatency = Date.now() - judgeStart;
    await sleep(config.judgeSleepMs);

    // ── Step 6: Constitutional critique ──
    let critique: CritiqueResult = { pass: true, violations: [] };
    let critiqueLatency = 0;

    if (!skipCritique && kiraResponse.length > 0) {
      const critiqueStart = Date.now();
      try {
        const critiquePromptText = buildCritiquePrompt(
          entry.question,
          kiraResponse,
          contextChunks > 0,
        );
        const critiqueRaw = await callBackend(
          config.judgeBackend,
          [{ role: "user", content: critiquePromptText }],
          0.1,
          512,
        );
        critique = parseCritiqueResponse(critiqueRaw);
      } catch (err) {
        console.log(
          `   Critique failed for ${entry.id}: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
      critiqueLatency = Date.now() - critiqueStart;
      await sleep(config.judgeSleepMs);
    }
