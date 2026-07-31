/* Local-only dictated-text confidence and homophone detector.
 * No audio access, network calls, background listening, key generation, or execution.
 */
(function (global) {
  'use strict';

  var HOMOPHONES = {
    pytest: ['pie', 'py test', 'pi test', 'pie test'],
    push: ['pushed', 'posh', 'put'],
    branch: ['brunch', 'branched'],
    key: ['kee', 'keys', 'keyed'],
    main: ['mane', 'mean'],
    merge: ['murj', 'marriage'],
    hypercorn: ['hyper corn', 'hypercon', 'hyper khan'],
    cosign: ['co sign', 'co-sign'],
    ghcr: ['g h c r', 'g h c are', 'ghcr'],
    'feature/canonical-governance-core': [
      'feature canonical governance core',
      'canonical governance core',
      'feature slash canonical governance core'
    ]
  };

  var REPOSITORY_TERMS = [
    'feature/canonical-governance-core',
    'canonical governance core',
    'ghcr.io',
    'ghcr',
    'cosign',
    'co sign',
    'hypercorn',
    'hyper corn',
    'aebdf65b78e4a82c6a22edebe378dc2e682cdd28'
  ];

  var HIGH_RISK = [
    'push', 'merge', 'delete', 'main', 'branch', 'key', 'keys',
    'sign', 'cosign', 'publish', 'deploy', 'release', 'cloud',
    'remote', 'hypercorn', 'ghcr', 'pytest'
  ];

  var LOCAL_FIRST_BLOCKS = [
    'cloud', 'remote provider', 'remote agent', 'hosted runner',
    'ghcr', 'ghcr.io', 'fulcio', 'rekor', 'cosign sign'
  ];

  function normalize(value) {
    return String(value || '')
      .toLowerCase()
      .replace(/[“”‘’]/g, "'")
      .replace(/[^\w\s./:-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function includesTerm(text, term) {
    var escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp('(^|\\s)' + escaped + '(?=\\s|$)', 'i').test(text);
  }

  function findCandidates(transcript) {
    var text = normalize(transcript);
    var candidates = [];

    Object.keys(HOMOPHONES).forEach(function (canonical) {
      HOMOPHONES[canonical].forEach(function (spokenVariant) {
        if (includesTerm(text, spokenVariant) && spokenVariant !== canonical) {
          candidates.push({
            canonical: canonical,
            heard: spokenVariant,
            confidence: 'possible',
            repositoryAware: REPOSITORY_TERMS.indexOf(canonical) !== -1
          });
        }
      });
    });

    return candidates;
  }

  function findRepositoryTerms(transcript) {
    var text = normalize(transcript);
    return REPOSITORY_TERMS.filter(function (term) {
      return text.indexOf(term.toLowerCase()) !== -1;
    });
  }

  function findRiskTerms(transcript) {
    var text = normalize(transcript);
    return HIGH_RISK.filter(function (term) {
      return includesTerm(text, term);
    });
  }

  function hasLocalFirstConflict(transcript) {
    var text = normalize(transcript);
    return LOCAL_FIRST_BLOCKS.some(function (term) {
      return text.indexOf(term) !== -1;
    });
  }

  function analyze(input) {
    input = input || {};
    var transcript = String(input.transcript || '');
    var confidence = typeof input.confidence === 'number'
      ? Math.max(0, Math.min(1, input.confidence))
      : null;
    var candidates = findCandidates(transcript);
    var repositoryTerms = findRepositoryTerms(transcript);
    var riskTerms = findRiskTerms(transcript);
    var localFirstConflict = hasLocalFirstConflict(transcript);
    var level = 'none';
    var reasons = [];

    if (localFirstConflict) {
      level = 'blocked';
      reasons.push('The request conflicts with the local-first policy.');
    } else if (riskTerms.length > 0) {
      level = 'required';
      reasons.push('The transcript contains a protected action or sensitive term.');
    } else if (candidates.length > 0 || repositoryTerms.length > 0) {
      level = 'review';
      reasons.push('A repository term or word may have been transcribed incorrectly.');
    } else if (confidence !== null && confidence < 0.82) {
      level = 'review';
      reasons.push('Speech-recognition confidence is below the local threshold.');
    }

    if (candidates.length > 0) reasons.push('Possible corrections were detected.');
    if (repositoryTerms.length > 0) reasons.push('A repository-specific term was detected.');

    return {
      rawTranscript: transcript,
      normalizedTranscript: normalize(transcript),
      confidence: confidence,
      candidates: candidates,
      repositoryTerms: repositoryTerms,
      riskTerms: riskTerms,
      localFirstConflict: localFirstConflict,
      level: level,
      needsConfirmation: level === 'review' || level === 'required',
      blocked: level === 'blocked',
      reasons: reasons
    };
  }

  function readBack(result) {
    var text = 'I heard: "' + result.rawTranscript + '"';

    if (result.candidates.length) {
      text += '. Possible correction: ' + result.candidates.map(function (candidate) {
        return '"' + candidate.canonical + '" instead of "' + candidate.heard + '"';
      }).join('; ');
    }

    if (result.repositoryTerms.length) {
      text += '. Repository terms detected: ' + result.repositoryTerms.join(', ');
    }

    if (result.blocked) {
      text += '. This conflicts with the local-first policy, so I will not continue.';
    } else if (result.needsConfirmation) {
      text += '. Should I use the transcript as heard, use the suggested correction, or cancel?';
    }

    return text;
  }

  global.SovereignVoiceConfirmation = {
    analyze: analyze,
    readBack: readBack,
    normalize: normalize,
    homophones: HOMOPHONES,
    repositoryTerms: REPOSITORY_TERMS
  };
}(typeof window !== 'undefined' ? window : globalThis));
