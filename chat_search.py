import asyncio
import json
import logging

from embedders import embedding_manager
from tidb import TiDBManager

logger = logging.getLogger(__name__)
CANDIDATE_LIMIT = 20
RESULT_LIMIT = 5
INDEX_BATCH_SIZE = 32
INDEX_INTERVAL_SECONDS = 30
RRF_RANK_CONSTANT = 60


def embedding_model_key():
    return f"reply-v1:{embedding_manager.model_name}"


def index_chat_batch(after_id):
    model_key = embedding_model_key()
    with TiDBManager.chat_session() as db:
        messages = db.get_unindexed_chats(model_key, after_id=after_id, limit=INDEX_BATCH_SIZE)
        if not messages:
            return None

        texts = []
        for message in messages:
            text = message["content"][:700]
            if message["reply_content"]:
                text += f"\nIn reply to: {message['reply_content'][:250]}"
            texts.append(text)

        embeddings = embedding_manager.get_embeddings(texts)
        db.store_chat_embeddings([
            (message["message_id"], model_key, message["channel_id"], json.dumps(vector, allow_nan=False))
            for message, vector in zip(messages, embeddings, strict=True)
        ])
        return messages[-1]["id"]


def create_chat_index():
    with TiDBManager.chat_session() as db:
        db.create_chat_embedding_table()


async def maintain_chat_index():
    """Backfill the transcript and periodically pick up newly stored messages."""
    ready = False
    after_id = 0
    while True:
        try:
            if not ready:
                await asyncio.to_thread(create_chat_index)
                ready = True
            last_id = await asyncio.to_thread(index_chat_batch, after_id)
            if last_id is not None:
                after_id = last_id
                continue
            # Check earlier IDs again after reaching the end, since inserts can commit out of order.
            after_id = 0
        except Exception as error:
            logger.warning("Chat embedding index could not advance (%s)", type(error).__name__)
        await asyncio.sleep(INDEX_INTERVAL_SECONDS)


def fuse_chat_rankings(keyword_ids, semantic_ids):
    scores = {}
    for ranking in (keyword_ids, semantic_ids):
        for rank, message_id in enumerate(dict.fromkeys(ranking), start=1):
            scores[message_id] = scores.get(message_id, 0) + 1 / (RRF_RANK_CONSTANT + rank)
    return sorted(scores, key=scores.__getitem__, reverse=True)


def search_chat_history(keywords, channel_id, *, query=None, exclude_message_id=None):
    """Combine scoped keyword and semantic matches, then read original messages."""
    if not channel_id:
        raise ValueError("A channel ID is required for chat search")

    terms = [term.strip() for term in keywords if term.strip()]
    semantic_query = (query or "").strip() or " ".join(terms)
    if not semantic_query:
        return [], []

    unavailable = []
    keyword_ids = []
    semantic_ids = []
    with TiDBManager.chat_session() as db:
        if terms:
            try:
                keyword_hits = db.get_chats(
                    terms, channel_id, exclude_message_id=exclude_message_id, limit=CANDIDATE_LIMIT,
                )
                keyword_ids = [hit["message_id"] for hit in keyword_hits]
            except Exception as error:
                logger.warning("Chat keyword search failed (%s)", type(error).__name__)
                unavailable.append("keyword")

        try:
            embedding = embedding_manager.get_embedding(semantic_query[:1_000])
            semantic_ids = db.get_semantic_chat_ids(
                json.dumps(embedding, allow_nan=False), embedding_model_key(), channel_id,
                exclude_message_id=exclude_message_id, limit=CANDIDATE_LIMIT,
            )
        except Exception as error:
            logger.warning("Chat semantic search failed (%s)", type(error).__name__)
            unavailable.append("semantic")

        if len(unavailable) == (2 if terms else 1):
            raise RuntimeError("Chat search is unavailable")
        ranked_ids = fuse_chat_rankings(keyword_ids, semantic_ids)
        messages = db.get_chat_search_messages(ranked_ids, channel_id, exclude_message_id=exclude_message_id)

    results = []
    included_ids = set()
    for message_id in ranked_ids:
        if message_id in included_ids or message_id not in messages:
            continue
        message = messages[message_id]
        included_ids.add(message_id)
        parent_id = message["reply_message_id"]
        if parent_id and message["reply_content"] and parent_id not in included_ids:
            included_ids.add(parent_id)
        else:
            message["reply_message_id"] = None
        results.append(message)
        if len(results) == RESULT_LIMIT:
            break
    return results, unavailable
