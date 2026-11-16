/* A.T.O.M.I.X. Engine Tools for Blockbench (by AtomicX).
 * Universal Animation Linter & Pack Exporter (non-combat).
 * Adds two actions to File > Export:
 *   - "Atomix Engine: Check Universal Names"
 *   - "Atomix Engine: Export Animation Pack (.pack.json)"
 * Load via File > Plugins > Load Plugin from File. */
(function () {
    let checkAction, packAction;

    function boneNames() {
        const names = new Set();
        (typeof Group !== 'undefined' ? Group.all : []).forEach(g => names.add(g.name));
        return names;
    }

    function animators(anim) {
        const out = [];
        for (const key in anim.animators) {
            const a = anim.animators[key];
            if (a && a.type === 'bone') out.push(a);
        }
        return out;
    }

    function shortName(n) { return n.substring(n.lastIndexOf('.') + 1); }

    function runCheck() {
        const bones = boneNames();
        const problems = [], notes = [];
        if (!bones.size) problems.push('The model has no bones (groups).');
        if (!Animation.all.length) problems.push('The project has no animations.');
        Animation.all.forEach(anim => {
            if (!anim.name.startsWith('animation.')) problems.push(`"${anim.name}": Bedrock animation names should start with "animation." (e.g. animation.entity.walk).`);
            animators(anim).forEach(a => {
                if (!bones.has(a.name)) problems.push(`"${anim.name}": animates bone "${a.name}" but the model has no bone with that exact name (case-sensitive).`);
            });
            if (anim.loop === 'once' && /idle|walk|run|swim|fly/i.test(anim.name)) notes.push(`"${anim.name}" looks like a repeating locomotion clip but Loop is "once".`);
            if (!(anim.length > 0)) problems.push(`"${anim.name}": length is 0.`);
        });

        let msg = problems.length ? 'Problems:\n- ' + problems.join('\n- ') : 'All bone and clip names match cleanly!';
        if (notes.length) msg += '\n\nNotes:\n- ' + notes.join('\n- ');
        Blockbench.showMessageBox({ title: 'AtomiX Engine: Check Names', message: msg.replace(/\n/g, '<br>'), icon: problems.length ? 'warning' : 'check' });
    }

    function exportPack() {
        if (!Animation.all.length) return Blockbench.showQuickMessage('No animations to export', 2000);
        const base = (Project.geometry_name || Project.name || 'model').replace(/\.geo$/, '');
        new Dialog({
            id: 'atomix_engine_pack_dialog',
            title: 'AtomiX Engine: Export Universal Animation Pack',
            form: {
                namespace: { label: 'Namespace (mod/pack id)', type: 'text', value: 'mymod' },
                model: { label: 'Target Model ID (no extension)', type: 'text', value: base },
                file: { label: 'Animation File Name (no extension)', type: 'text', value: base },
                priority: { label: 'Priority', type: 'number', value: 10 },
                fade: { label: 'Default Inertialization Fade (s)', type: 'number', value: 0.15 }
            },
            onConfirm(f) {
                const states = {};
                Animation.all.forEach(a => {
                    states[shortName(a.name)] = { file: `${f.namespace}:${f.file}`, clip: a.name, fade: f.fade };
                });
                const pack = { target: `${f.namespace}:${f.model}`, priority: f.priority, states };
                Blockbench.export({
                    type: 'AtomiX Animation Pack', extensions: ['json'], name: f.file + '.pack',
                    content: JSON.stringify(pack, null, 2)
                });
            }
        }).show();
    }

    Plugin.register('atomix_engine_tools', {
        title: 'A.T.O.M.I.X. Engine — Universal Animation Tools',
        author: 'AtomicX',
        description: 'Validates bone/clip names and exports universal .pack.json state mappings for A.T.O.M.I.X. Engine.',
        icon: 'fa-atom',
        version: '1.1.0',
        variant: 'both',
        onload() {
            checkAction = new Action('atomix_engine_check', { name: 'AtomiX Engine: Check Names', icon: 'fa-check-double', click: runCheck });
            packAction = new Action('atomix_engine_export_pack', { name: 'AtomiX Engine: Export Pack File', icon: 'fa-file-export', click: exportPack });
            MenuBar.addAction(checkAction, 'file.export');
            MenuBar.addAction(packAction, 'file.export');
        },
        onunload() {
            checkAction && checkAction.delete();
            packAction && packAction.delete();
        }
    });
})();
