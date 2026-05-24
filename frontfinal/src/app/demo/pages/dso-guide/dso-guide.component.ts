import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-dso-guide',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dso-guide.component.html',
  styleUrls: ['./dso-guide.component.scss']
})
export class DsoGuideComponent {

  readonly tc: Record<string, { bg: string; border: string; dot: string; val: string; ref: string }> = {
    crit:    { bg: 'rgba(239,68,68,0.07)',    border: 'rgba(239,68,68,0.3)',    dot: '#dc2626', val: '#dc2626', ref: 'rgba(239,68,68,0.12)'    },
    warn:    { bg: 'rgba(245,158,11,0.07)',   border: 'rgba(245,158,11,0.3)',   dot: '#d97706', val: '#d97706', ref: 'rgba(245,158,11,0.12)'   },
    ok:      { bg: 'rgba(34,197,94,0.07)',    border: 'rgba(34,197,94,0.3)',    dot: '#16a34a', val: '#16a34a', ref: 'rgba(34,197,94,0.12)'    },
    info:    { bg: 'rgba(29,78,216,0.07)',    border: 'rgba(29,78,216,0.3)',    dot: '#1d4ed8', val: '#1d4ed8', ref: 'rgba(29,78,216,0.12)'    },
    neutral: { bg: 'rgba(108,117,125,0.07)', border: 'rgba(108,117,125,0.2)', dot: '#94a3b8', val: '#6c757d', ref: 'rgba(108,117,125,0.12)' },
  };

  t(level: string) { return this.tc[level] ?? this.tc['neutral']; }

  dsos = [
    {
      num: 'Objective 1', c1: '#1e40af', c2: '#1d4ed8', r: '30, 64, 175',
      icon: 'icon-shuffle',
      title: 'Handover prediction', tag: 'Binary classification',
      label: {
        title: 'Handover event – 0 / 1',
        code: 'handover = 1\nif cell_index[t] ≠ cell_index[t+1]\nwithin same session\n\nhandover = 0 otherwise',
        classes: ['0 – no handover', '1 – handover']
      },
      features: [
        { r: 1, name: 'rsrq',     pct: 100, desc: 'signal quality'  },
        { r: 2, name: 'velocity', pct: 87,  desc: 'UE speed'        },
        { r: 3, name: 'sinr',     pct: 72,  desc: 'interference'    },
        { r: 4, name: 'tx_power', pct: 72,  desc: 'emission power'  },
        { r: 5, name: 'cqi',      pct: 70,  desc: 'channel quality' },
        { r: 6, name: 'zone_id',  pct: 53,  desc: 'geographic zone' },
        { r: 7, name: 'rsrp_T1',  pct: 44,  desc: 'signal trend'   },
        { r: 8, name: 'rsrp',     pct: 42,  desc: 'coverage'        },
      ],
      thresholds: [
        { level: 'crit', val: '≥ 0.70',    label: 'P1 critical – handover imminent · Event A3 confirmed', ref: 'TS 38.331 §5.5.4.4' },
        { level: 'warn', val: '0.50–0.70', label: 'P2 high – Event A3 verifying · TTT not elapsed',       ref: 'TS 38.331 §6.3.2'   },
        { level: 'ok',   val: '< 0.50',    label: 'P3 – no handover expected · serving cell stable',       ref: 'TS 38.300 §15.1'    },
      ],
      note: 'TTT values: 0 ms – 5120 ms · A3-offset configurable per cell · Event A3: 3GPP TS 38.331'
    },
    {
      num: 'Objective 2', c1: '#d97706', c2: '#b45309', r: '217, 119, 6',
      icon: 'icon-trending-down',
      title: 'Signal drop detection', tag: 'Binary classification',
      label: {
        title: 'RSRP drop – 0 / 1',
        code: 'rsrp_drop = 1\nif min(rsrp[t+1..t+5])\n   − rsrp[t] < −6 dBm\n\nComputed on raw RSRP\n(not preprocessed values)',
        classes: ['0 – no drop', '1 – drop detected']
      },
      features: [
        { r: 1, name: 'rsrp',       pct: 100, desc: 'main signal'   },
        { r: 2, name: 'rsrp_T1–T5', pct: 90,  desc: 'history T–5'  },
        { r: 3, name: 'sinr',       pct: 72,  desc: 'correlation'   },
        { r: 4, name: 'rsrq',       pct: 65,  desc: 'quality'       },
        { r: 5, name: 'velocity',   pct: 55,  desc: 'mobility'      },
        { r: 6, name: 'rsrp_gap',   pct: 48,  desc: 'vs neighbour'  },
        { r: 7, name: 'zone_id',    pct: 38,  desc: 'geographic'    },
        { r: 8, name: 'cqi',        pct: 30,  desc: 'channel'       },
      ],
      thresholds: [
        { level: 'crit', val: 'Δ RSRP < −6 dBm', label: 'Drop label = 1 · computed over T+1 to T+5 measurements', ref: 'TS 38.133 §10.1.6'   },
        { level: 'warn', val: 'RSRP ≤ −110 dBm',  label: 'Weak coverage · P1 alert · Event A2 threshold',          ref: 'TS 38.133 §10.1.6.1' },
        { level: 'warn', val: 'RSRP ≤ −100 dBm',  label: 'Degraded signal · P2 alert · serving below threshold',   ref: 'TS 36.331 §5.5.4.3'  },
        { level: 'ok',   val: 'RSRP > −100 dBm',  label: 'Normal signal · no drop risk',                           ref: 'TS 38.133 §10.1.6'   },
      ],
      note: 'Window: 5 future measurements · raw RSRP · dataset median: −88.0 dBm · 3GPP TS 38.133 §10.1.6'
    },
    {
      num: 'Objective 3', c1: '#16a34a', c2: '#15803d', r: '22, 163, 74',
      icon: 'icon-target',
      title: 'Next best cell', tag: 'Multi-class · 50 classes',
      label: {
        title: 'Target cell – 50 candidates',
        code: 'next_cell = cell_index[t+1]\nat handover event\n\nEncoded via LabelEncoder\n→ 50 most frequent target\n   cells in training set',
        classes: ['Cell-0 – Cell-49', 'LabelEncoder']
      },
      features: [
        { r: 1, name: 'latitude',   pct: 100, desc: 'GPS position'   },
        { r: 2, name: 'longitude',  pct: 98,  desc: 'GPS position'   },
        { r: 3, name: 'zone_id',    pct: 82,  desc: 'zone context'   },
        { r: 4, name: 'rsrp_neigh', pct: 74,  desc: 'neighbour sig.' },
        { r: 5, name: 'earfcn',     pct: 68,  desc: 'frequency band' },
        { r: 6, name: 'velocity',   pct: 58,  desc: 'mobility'       },
        { r: 7, name: 'bearing',    pct: 48,  desc: 'direction'      },
        { r: 8, name: 'rsrp',       pct: 40,  desc: 'serving signal' },
      ],
      thresholds: [
        { level: 'info',    val: 'Top-1 accuracy',   label: '78.5% – correct target cell predicted on first guess', ref: 'TS 38.331 §5.5.4.3' },
        { level: 'ok',      val: 'Top-3 accuracy',   label: '97.3% – correct cell appears in top-3 candidates',     ref: 'TS 38.331 §5.5.4.3' },
        { level: 'neutral', val: 'A3 offset rule',   label: 'RSRP_neigh > RSRP_serv + offset → candidate valid',   ref: 'TS 38.331 §5.5.4.4' },
        { level: 'neutral', val: 'PCI verification', label: 'Physical cell ID used to filter valid target cells',   ref: 'TS 38.211 §7.4.2'   },
      ],
      note: 'Ping-pong prevention: exclude cells triggering return HO < 1s · 3GPP TS 38.331 §5.5.4.3'
    },
    {
      num: 'Objective 4', c1: '#7c3aed', c2: '#6d28d9', r: '124, 58, 237',
      icon: 'icon-layers',
      title: 'Handover type classification', tag: 'Multi-class · 8 classes',
      label: {
        title: 'HO type – 8 classes (NB2 FE-2)',
        code: 'ho_type_enc = 0 – 7\nOrdinalEncoder from\nho_type raw column\n\nno_handover:  77.9%\nintra_freq:   15.4%\ninter_freq:    6.1%\ninter_RAT_NR:  0.6%',
        classes: ['no_handover', 'intra_freq', 'inter_freq', 'inter_RAT_NR', '+4 rare types']
      },
      features: [
        { r: 1, name: 'earfcn',     pct: 100, desc: 'frequency band' },
        { r: 2, name: 'sinr',       pct: 88,  desc: 'interference'   },
        { r: 3, name: 'velocity',   pct: 78,  desc: 'mobility'       },
        { r: 4, name: 'rsrp_neigh', pct: 70,  desc: 'neighbour'      },
        { r: 5, name: 'zone_id',    pct: 60,  desc: 'zone context'   },
        { r: 6, name: 'ss_sinr',    pct: 52,  desc: '5G NR signal'   },
        { r: 7, name: 'ta',         pct: 42,  desc: 'UE distance'    },
        { r: 8, name: 'cqi',        pct: 32,  desc: 'channel qual.'  },
      ],
      thresholds: [
        { level: 'neutral', val: 'no_handover',   label: '77.9% – serving cell maintained, no transition',       ref: 'TS 38.331 §5.3'     },
        { level: 'info',    val: 'intra_freq',    label: '15.4% – same frequency band, EARFCN unchanged',        ref: 'TS 38.331 §5.5.4.2' },
        { level: 'warn',    val: 'inter_freq',    label: '6.1% – different frequency band, EARFCN changes',      ref: 'TS 38.331 §5.5.4.3' },
        { level: 'crit',    val: 'inter_RAT_NR',  label: '0.6% – LTE → NR transition, ss_rsrp/ss_sinr active',  ref: 'TS 38.331 §5.5.4.9' },
      ],
      note: 'Heavy class imbalance: 77.9% no_handover · 3GPP TS 38.331 §5.5 – handover types and procedures'
    }
  ];

  isLast(i: number): boolean { return i === this.dsos.length - 1; }
}
