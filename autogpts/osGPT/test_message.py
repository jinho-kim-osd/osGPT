from langchain.schema import SystemMessage, HumanMessage
from forge.utils import chat_completion_request
from langchain.adapters.openai import convert_openai_messages, convert_message_to_dict
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    messages_from_dict,
    messages_to_dict,
)


from litellm import completion, acompletion, AuthenticationError, InvalidRequestError

# LOG = ForgeLogger(__name__)


# @retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
# async def chat_completion_request(
#     model, messages, **kwargs
# ) -> typing.Union[typing.Dict[str, typing.Any], Exception]:
#     """Generate a response to a list of messages using OpenAI's API"""
#     try:
#         kwargs["model"] = model
#         kwargs["messages"] = messages

#         resp = await acompletion(**kwargs)
#         return resp
#     except AuthenticationError as e:
#         LOG.exception("Authentication Error")
#     except InvalidRequestError as e:
#         LOG.exception("Invalid Request Error")
#     except Exception as e:
#         LOG.error("Unable to generate ChatCompletion response")
#         LOG.error(f"Exception: {e}")
#         raise
# Message = Union[AIMessage, HumanMessage, SystemMessage]

messages = [SystemMessage(content="Say words in reverse"), HumanMessage(content="Good morning")]
print(completion(model="gpt-4", messages=[convert_message_to_dict(message) for message in messages]))