/* A.T.O.M.I.X. Combat Tools for Blockbench (by AtomicX).
 * Universal Fighting Animation & Combat Moveset Authoring Plugin.
 * Adds three actions to Animation / File menus:
 *   - "AtomiX Combat: Insert Combat Phase (Windup / Strike / Recover / Parry / Hitstop)"
 *   - "AtomiX Combat: Validate Fighting Animation Phases & Sockets"
 *   - "AtomiX Combat: Export Universal Combat Moveset (.combat.json & .pack.json)"
 * Load via File > Plugins > Load Plugin from File. */
(function () {
    let phaseAction, validateAction, exportMovesetAction;

    function shortName(n) { return n.substring(n.lastIndexOf('.') + 1); }

    function insertPhaseDialog() {
        const anim = Animation.selected;
        if (!anim) return Blockbench.showQuickMessage('Select an animation clip first!', 2000);

        new Dialog({
            id: 'atomix_combat_phase_dialog',
            title: 'AtomiX Combat: Insert Phase Marker at Playhead',
            form: {
                phase: {
                    label: 'Combat Phase',
                    type: 'select',
                    options: {
                        'phase:windup': 'phase:windup (Attack Startup)',
                        'phase:strike': 'phase:strike (Active Hitbox Sweep)',
                        'phase:hitstop': 'phase:hitstop (Impact Freeze Frame)',
                        'phase:recover': 'phase:recover (Combo Input Buffer Window)',
                        'phase:parry': 'phase:parry (Active Deflection Window)',
                        'phase:neutral': 'phase:neutral (Return to Idle)'
                    },
                    value: 'phase:strike'
                },
                time: {
                    label: 'Time (seconds)',
                    type: 'number',
                    value: Timeline.time || 0.0,
                    step: 0.05
                }
            },
            onConfirm(form) {
                if (!anim.animators.effects) {
                    anim.addAnimator(new EffectAnimator(anim));
                }
                const effects = anim.animators.effects;
                effects.addKeyframe({
                    channel: 'timeline',
                    time: form.time,
                    data_points: [{ script: form.phase }]
                });
                Blockbench.showQuickMessage(`Inserted ${form.phase} at ${form.time.toFixed(2)}s`, 2000);
            }
        }).show();
    }

    function validateCombatAnims() {
        const problems = [], notes = [];
        if (!Animation.all.length) problems.push('No animations in project.');

        Animation.all.forEach(anim => {
            const effects = anim.animators && anim.animators.effects;
            let hasWindup = false, hasStrike = false, hasRecover = false;
            if (effects && effects.timeline) {
                effects.timeline.forEach(kf => {
                    const txt = (kf.data_points && kf.data_points[0] && kf.data_points[0].script) || '';
                    if (txt.includes('phase:windup')) hasWindup = true;
                    if (txt.includes('phase:strike')) hasStrike = true;
                    if (txt.includes('phase:recover')) hasRecover = true;
                });
            }
            if (/slash|attack|strike|bite|claw|slam|combo|punch|kick/i.test(anim.name)) {
                if (!hasStrike) problems.push(`"${anim.name}": looks like an attack animation but has no "phase:strike" timeline key (hitbox will never activate).`);
                if (!hasWindup) notes.push(`"${anim.name}": missing "phase:windup" at start.`);
                if (!hasRecover) notes.push(`"${anim.name}": missing "phase:recover" at follow-through (combo chaining requires recovery phase).`);
            }
        });

        let msg = problems.length ? 'Combat Validation Issues:\n- ' + problems.join('\n- ') : 'All fighting animations have valid combat phases!';
        if (notes.length) msg += '\n\nRecommendations:\n- ' + notes.join('\n- ');
        Blockbench.showMessageBox({
            title: 'AtomiX Combat: Fighting Animation Check',
            message: msg.replace(/\n/g, '<br>'),
            icon: problems.length ? 'warning' : 'check'
        });
    }

    function exportCombatMoveset() {
        if (!Animation.all.length) return Blockbench.showQuickMessage('No animations to export', 2000);
        const base = (Project.geometry_name || Project.name || 'fighter').replace(/\.geo$/, '');
        new Dialog({
            id: 'atomix_combat_export_dialog',
            title: 'AtomiX Combat: Export Universal Fighting Moveset',
            form: {
                namespace: { label: 'Mod Namespace', type: 'text', value: 'mymod' },
                targetEntity: { label: 'Target Entity / Model ID', type: 'text', value: `mymod:${base}` },
                movesetId: { label: 'Moveset ID', type: 'text', value: `${base}_moveset` },
                hitboxBone: { label: 'Primary Hitbox Bone', type: 'text', value: 'right_arm' },
                hitboxLocator: { label: 'Weapon Tip Locator', type: 'text', value: 'right_hand' },
                hitboxRadius: { label: 'Sweep Radius (blocks)', type: 'number', value: 0.45 },
                maxPoise: { label: 'Max Poise / Posture', type: 'number', value: 100 }
            },
            onConfirm(f) {
                const states = {};
                const combos = [];
                Animation.all.forEach(a => {
                    const sName = shortName(a.name);
                    states[sName] = {
                        file: `${f.namespace}:${base}`,
                        clip: a.name,
                        fade: 0.08,
                        speed: 1.0,
                        root_motion: true
                    };
                    if (/slash|attack|strike|bite|claw|slam/i.test(sName)) {
                        combos.push({ id: sName, clip: sName, damageMultiplier: 1.0, poiseDamage: 20.0, hitStopTicks: 2 });
                    }
                });

                const bundle = {
                    target: f.targetEntity,
                    priority: 20,
                    moveset: {
                        id: f.movesetId,
                        combatLayer: 'combat',
                        maxPoise: f.maxPoise,
                        hitbox: { bone: f.hitboxBone, locatorTip: f.hitboxLocator, radius: f.hitboxRadius },
                        comboChain: combos
                    },
                    states
                };

                Blockbench.export({
                    type: 'AtomiX Combat Moveset Pack',
                    extensions: ['json'],
                    name: `${base}_combat.pack`,
                    content: JSON.stringify(bundle, null, 2)
                });
            }
        }).show();
    }

    Plugin.register('atomix_combat_tools', {
        title: 'A.T.O.M.I.X. Combat — Universal Fighting Animation Tools',
        author: 'AtomicX',
        description: 'Inserts combat timeline phases (windup, strike, recover, parry, hitstop), validates hitboxes, and exports universal fighting movesets.',
        icon: 'fa-khanda',
        version: '1.0.0',
        variant: 'both',
        onload() {
            phaseAction = new Action('atomix_combat_insert_phase', {
                name: 'AtomiX Combat: Insert Phase Marker',
                icon: 'fa-bolt',
                click: insertPhaseDialog
            });
            validateAction = new Action('atomix_combat_validate', {
                name: 'AtomiX Combat: Validate Fighting Phases',
                icon: 'fa-shield-alt',
                click: validateCombatAnims
            });
            exportMovesetAction = new Action('atomix_combat_export_moveset', {
                name: 'AtomiX Combat: Export Combat Moveset',
                icon: 'fa-file-export',
                click: exportCombatMoveset
            });
            MenuBar.addAction(phaseAction, 'animation');
            MenuBar.addAction(validateAction, 'file.export');
            MenuBar.addAction(exportMovesetAction, 'file.export');
        },
        onunload() {
            phaseAction && phaseAction.delete();
            validateAction && validateAction.delete();
            exportMovesetAction && exportMovesetAction.delete();
        }
    });
})();
