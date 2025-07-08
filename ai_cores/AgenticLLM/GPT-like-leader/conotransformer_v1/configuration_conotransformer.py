from ...utils import logging

from ...modeling_rope_utils import rope_config_validation
from ...configuration_utils import PretrainedConfig

DEEPSEEK_PRETRAINED_CONFIG_ARCHIVE_MAP = {}
logger = logging.get_logger(__name__)


class ConoTransformerConfig(PretrainedConfig):
   
    model_type = "conotransformer"
    keys_to_ignore_at_inference = ["past_key_values"]
    base_model_tp_plan = {  # TODO: only replicate attention layers when > first_k_dense_replace
        "layers.*.mlp.experts.*.gate_proj": "local_colwise",
        "layers.*.mlp.experts.*.up_proj": "local_colwise",
        "layers.*.mlp.experts.*.down_proj": "local_rowwise",
        "layers.*.mlp.experts.*": "local",  # each expert is wrapped in a module list
        "layers.*.mlp.shared_experts.gate_proj": "local_colwise",
        "layers.*.mlp.shared_experts.up_proj": "local_colwise",
        "layers.*.mlp.shared_experts.down_proj": "local_rowwise",
        "layers.*.mlp.shared_experts": "local",
        "layers.*.mlp.gate_proj": "local_colwise",
        "layers.*.mlp.up_proj": "local_colwise",
        "layers.*.mlp.down_proj": "local_rowwise",
        "layers.*.mlp": "gather",  # This is the only moment where results are gathered
    }
    base_model_pp_plan = {
        "embed_tokens": (["input_ids"], ["inputs_embeds"]),
        "layers": (["hidden_states", "attention_mask"], ["hidden_states"]),
        "norm": (["hidden_states"], ["hidden_states"]),
    }

    def __init__(

        # Basic parameters
        self,
        vocab_size=129280,
        hidden_size=7168,
        intermediate_size=18432,
        moe_intermediate_size=2048,
        num_hidden_layers=61,
        num_attention_heads=128,
        num_key_value_heads=128,

        # MoE parameters
        n_shared_experts=1,
        n_routed_experts=256,
        routed_scaling_factor=2.5,
        num_experts_per_tok=8,

        # LoRA parameters
        kv_lora_rank=512,
        q_lora_rank=1536,
        
        # MLP structure parameters
        qk_rope_head_dim=64,
        v_head_dim=128,
        qk_nope_head_dim=128,
        n_group=8,
        topk_group=4,
        first_k_dense_replace=3,
        norm_topk_prob=True,
        hidden_act="gelu_new",
        layer_norm_eps=1e-12,
        
        # Context window parameters
        max_position_embeddings=16384,
        initializer_range=0.02,
        rms_norm_eps=1e-6,
        scale_embedding=True,

        # Rotary position embeddings parameters
        use_cache=True,
        pretraining_tp=1,
        tie_word_embeddings=False,
        rope_theta=10000.0,
        rope_scaling={"type": "dynamic", "factor": 8.0},
        rope_interleave=True,
        attention_bias=True,
        
        # Dropout parameters
        attention_dropout=0.1,
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        layerdrop=0.0,
        activation_dropout=0.0,

        # Token IDs
        bos_token_id=0,
        pad_token_id=1, 
        eos_token_id=2, 

        **kwargs,
    ):
        
        # Basic parameters
        self.vocab_size = vocab_size
        self.max_position_embeddings = max_position_embeddings
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size
        self.moe_intermediate_size = moe_intermediate_size
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.intermediate_size = intermediate_size

        # MoE parameters
        self.n_routed_experts = n_routed_experts
        self.routed_scaling_factor = routed_scaling_factor
        self.num_experts_per_tok = num_experts_per_tok
        self.first_k_dense_replace = first_k_dense_replace
        self.n_group = n_group
        self.topk_group = topk_group
        self.norm_topk_prob = norm_topk_prob
        self.n_shared_experts = n_shared_experts

        # LoRA parameters
        self.kv_lora_rank = kv_lora_rank
        self.q_lora_rank = q_lora_rank

        # MLP structure parameters
        self.qk_rope_head_dim = qk_rope_head_dim
        self.v_head_dim = v_head_dim
        self.qk_nope_head_dim = qk_nope_head_dim
        self.qk_head_dim = qk_nope_head_dim + qk_rope_head_dim
        self.hidden_size = hidden_size
        
        # Dropout parameters
        self.activation_dropout = activation_dropout
        self.attention_probs_dropout_prob = attention_probs_dropout_prob
        self.hidden_dropout_prob = hidden_dropout_prob
        self.layerdrop = layerdrop
        self.attention_dropout = attention_dropout
        
        # Rotary position embeddings parameters
        self.rope_interleave = rope_interleave
        self.use_cache = use_cache
        self.rope_theta = rope_theta
        self.rope_scaling = rope_scaling
        self.attention_bias = attention_bias

        # MLP structure parameters
        self.head_dim = qk_rope_head_dim
        self.hidden_act = hidden_act
        self.layer_norm_eps = layer_norm_eps
        self.scale_embedding = scale_embedding
        self.num_key_value_heads = num_key_value_heads
        self.hidden_act = hidden_act
        self.initializer_range = initializer_range
        self.rms_norm_eps = rms_norm_eps
        self.pretraining_tp = pretraining_tp

        # for backward compatibility
        if num_key_value_heads is None:
            num_key_value_heads = num_attention_heads

        # Validate the correctness of rotary position embeddings parameters
        # BC: if there is a 'type' field, copy it it to 'rope_type'.
        if self.rope_scaling is not None and "type" in self.rope_scaling:
            self.rope_scaling["rope_type"] = self.rope_scaling["type"]

        if self.rope_scaling is not None:
            for key in ["beta_fast", "beta_slow", "factor"]:
                if key in self.rope_scaling:
                    self.rope_scaling[key] = float(self.rope_scaling[key])

        rope_config_validation(self)

        super().__init__(
            pad_token_id=pad_token_id,
            bos_token_id=bos_token_id,
            eos_token_id=eos_token_id,
            tie_word_embeddings=tie_word_embeddings,
            **kwargs,
        )

__all__ = ["ConoTransformerConfig"]