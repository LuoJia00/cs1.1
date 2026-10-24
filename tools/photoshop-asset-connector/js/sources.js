/* 三个数据源适配器：把 资产库 / 画布资产 / 本地素材 统一成 {id,name,url,kind,search,createdAt}。
 * 每个适配器暴露：load / optionsA / optionsB / items / exportTarget / doExport。 */
(function () {
  const state = DX.state;
  const net = DX.net;

  function itemIsImage(item) {
    if (!item) return false;
    if (item.kind) return item.kind === 'image';
    const text = String(item.url || item.name || '').toLowerCase().split(/[?#]/)[0];
    return /\.(png|jpe?g|webp|gif|avif|bmp)$/i.test(text);
  }

  function classificationText(cls) {
    if (!cls || typeof cls !== 'object') return '';
    const parts = [cls.summary];
    if (Array.isArray(cls.tags)) parts.push(cls.tags.join(' '));
    if (cls.categories && typeof cls.categories === 'object') {
      for (const v of Object.values(cls.categories)) if (Array.isArray(v)) parts.push(v.join(' '));
    }
    return parts.filter(Boolean).join(' ');
  }

  // 后端的图片/画布时间为毫秒，本地文件时间为秒，统一成毫秒。
  function timestamp(value) {
    if (value == null || value === '') return 0;
    const n = Number(value);
    if (Number.isFinite(n)) return n > 0 ? (n < 1e12 ? n * 1000 : n) : 0;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  }

  function sortItems(items, order) {
    if (order !== 'newest' && order !== 'oldest') return items.slice();
    const direction = order === 'oldest' ? 1 : -1;
    return items.map((item, index) => ({ item, index })).sort((a, b) => {
      const at = a.item.createdAt || 0;
      const bt = b.item.createdAt || 0;
      // 缺少时间的素材始终排在最后；同一时间保持原始顺序。
      if (!at && bt) return 1;
      if (at && !bt) return -1;
      return direction * (at - bt) || a.index - b.index;
    }).map((entry) => entry.item);
  }

  const adapters = {
    /* 图片资产 —— /api/asset-library */
    assets: {
      editable: true,
      async load() { state.raw.assets = (await net.apiGet('/api/asset-library')).library || null; },
      libraries() {
        const lib = state.raw.assets;
        return lib && Array.isArray(lib.libraries) ? lib.libraries : [];
      },
      optionsA() { return this.libraries().map((l) => ({ id: l.id, name: l.name || '资产库' })); },
      categoriesOf(aId) {
        const l = this.libraries().find((x) => x.id === aId) || this.libraries()[0];
        return l && Array.isArray(l.categories) ? l.categories : [];
      },
      optionsB(aId) {
        return this.categoriesOf(aId).map((c) => ({
          id: c.id,
          name: `${c.name || '分组'}${c.type === 'workflow' ? '（工作流）' : ''} · ${(c.items || []).length}`,
        }));
      },
      items(aId, bId) {
        const cat = this.categoriesOf(aId).find((c) => c.id === bId);
        if (!cat || cat.type === 'workflow') return [];
        return (cat.items || []).map((it) => ({
          id: it.id, name: it.name || '未命名', url: it.url, kind: it.kind || 'image',
          createdAt: timestamp(it.created_at),
          search: `${it.name || ''} ${it.caption || ''} ${classificationText(it.classification)}`.toLowerCase(),
        }));
      },
      exportTarget(aId, bId) {
        const cat = this.categoriesOf(aId).find((c) => c.id === bId);
        if (!cat || cat.type !== 'image') return null;
        return { label: cat.name || '分组' };
      },
      async doExport(aId, bId, name, buffer) {
        const url = await net.uploadInputBase64(buffer, name);     // 先上传拿 /assets 临时 url
        await net.apiSend('POST', '/api/asset-library/items', { library_id: aId, category_id: bId, url, name });
      },
    },

    /* 画布资产 —— /api/canvas-assets（只读） */
    canvas: {
      editable: false,
      async load() { state.raw.canvas = await net.apiGet('/api/canvas-assets'); },
      optionsA() {
        const cats = (state.raw.canvas && state.raw.canvas.categories) || [];
        return cats.map((c) => ({ id: c.id, name: `${c.name}` }));
      },
      optionsB(aId) {
        const all = (state.raw.canvas && state.raw.canvas.canvases) || [];
        const list = aId && aId !== 'all' ? all.filter((c) => (c.kind || 'classic') === aId) : all;
        return [{ id: '__all__', name: '全部画布' }].concat(
          list.map((c) => ({ id: c.id, name: `${c.title || '未命名画布'} · ${c.asset_count || 0}` }))
        );
      },
      items(aId, bId) {
        let list = (state.raw.canvas && state.raw.canvas.items) || [];
        if (aId && aId !== 'all') list = list.filter((it) => (it.canvas_kind || 'classic') === aId);
        if (bId && bId !== '__all__') list = list.filter((it) => it.canvas_id === bId);
        return list.map((it) => ({
          id: it.id, name: it.name || '未命名', url: it.url, kind: it.kind || 'image',
          createdAt: timestamp(it.created_at) || timestamp(it.canvas_updated_at) || timestamp(it.canvas_created_at),
          search: `${it.name || ''} ${it.canvas_title || ''} ${it.node_title || ''}`.toLowerCase(),
        }));
      },
      exportTarget() { return null; },
    },

    /* 本地素材 —— /api/local-assets */
    local: {
      editable: true,
      async load() { state.raw.local = await net.apiGet('/api/local-assets'); },
      optionsA() { return null; },
      folders() {
        const tree = state.raw.local && state.raw.local.tree;
        const out = [{ id: '', name: '全部素材' }];
        const walk = (node, depth) => {
          if (!node) return;
          for (const child of node.children || []) {
            out.push({ id: child.path, name: `${'　'.repeat(depth)}${child.name || child.path}` });
            walk(child, depth + 1);
          }
        };
        walk(tree, 0);
        return out;
      },
      optionsB() { return this.folders(); },
      items(_aId, bId) {
        let list = (state.raw.local && state.raw.local.items) || [];
        if (bId) list = list.filter((it) => it.folder === bId || String(it.folder || '').startsWith(`${bId}/`));
        return list.map((it) => ({
          id: it.id, name: it.name || '未命名', url: it.url, kind: it.kind || 'image',
          createdAt: timestamp(it.created_at),
          search: `${it.name || ''} ${it.caption || ''} ${classificationText(it.classification)}`.toLowerCase(),
        }));
      },
      exportTarget(_aId, bId) { return { label: bId || '全部素材' }; },
      async doExport(_aId, bId, name, buffer) {
        // 走 base64 import-urls（带 folder），避开 FormData；素材直接落到选中的本地文件夹
        const b64 = net.toBase64(buffer);
        const res = await net.apiSend('POST', '/api/local-assets/import-urls', {
          folder: bId || '',
          items: [{ data: `data:image/png;base64,${b64}`, name, content_type: 'image/png' }],
        });
        const r = (res.items || [])[0];
        if (r && r.ok === false) throw new Error(r.error || '导入失败');
      },
    },
  };

  DX.sources = {
    adapters,
    adapter() { return adapters[state.source]; },
    itemIsImage,
    classificationText,
    sortItems,
  };
})();
