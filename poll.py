from collections import defaultdict
from typing import Optional, Union
import disnake as discord
from disnake.ext.commands import Bot
from disnake import ApplicationCommandInteraction, Component
import peewee as pw
from datetime import datetime

DROPDOWN_ID = "movie dropdown"
SUGGEST_BUTTON_ID = "suggest a movie"
ABSTENTION = "Abstain from vote 👐"

db = pw.SqliteDatabase('db/polls.db')

class BaseModel(pw.Model):
    class Meta:
        database = db

class Poll(BaseModel):
    created_date = pw.DateTimeField(default=datetime.now)
    message_id = pw.BigIntegerField(primary_key=True)

class MovieOption(BaseModel):
    added_by_id = pw.BigIntegerField()
    name = pw.CharField()
    in_poll = pw.ForeignKeyField(Poll, backref="options")
    class Meta:
        constraints = [pw.SQL('UNIQUE (name, in_poll_id)')]

class Vote(BaseModel):
    what_for = pw.ForeignKeyField(MovieOption, backref="votes")
    in_poll = pw.ForeignKeyField(Poll, backref="votes")
    voter_id = pw.BigIntegerField(index=True)
    voter_nickname = pw.CharField()

db.connect()
db.create_tables([Poll, MovieOption, Vote])

def search_components(
    comps: Union[Component, list[Component]], 
    custom_id: str
) -> Optional[Component]:
    def check_comp(child: Component):
        if getattr(child, "custom_id", None) == custom_id:
            return True
    for comp in comps if isinstance(comps, list) else [comps]:
        if check_comp(comp):
            return comp
        else:
            for child in getattr(comp, "children", []):
                result = search_components(child, custom_id)
                if result is not None:
                    return result
            return None

class SuggestModal(discord.ui.Modal):
    def __init__(self):
        text_input = discord.ui.TextInput(
            label="🥺",
            custom_id="suggest_text_input",
            min_length=1,
            max_length=200
        )
        title = "Suggest a Film"
        custom_id = "suggestion modal for films"
        components = [text_input]
        super().__init__(title=title, custom_id=custom_id, components=components)
        
    async def callback(self, action: discord.ModalInteraction):
        added_movie = list(action.text_values.values())[0]
        if len(added_movie.strip()) == 0:
            await action.response.send_message("not valid", ephemeral=True)
            return
        original_message_id = action.message.id
        poll: Poll = Poll.get_or_create(message_id=original_message_id)[0]
        try:
            MovieOption.create(
                added_by_id=action.author.id, 
                name=added_movie, 
                in_poll=original_message_id).save()
        except: pass
        await action.response.edit_message(
            content=poll_model_to_vote_count(poll),
            view=poll_model_to_view(poll))

def poll_model_to_view(poll: Optional[Poll]=None) -> discord.ui.View:
    options = [x.name for x in poll.options] if poll != None else []
    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Select(
            custom_id=DROPDOWN_ID,
            options = options+[ABSTENTION]
        )
    )
    view.add_item(
        discord.ui.Button(
            label="Suggest a Film",
            custom_id=SUGGEST_BUTTON_ID
        )
    )
    return view

def poll_model_to_vote_count(poll: Poll) -> str:
    movie_votes = defaultdict(lambda: 0)
    movie_voters = defaultdict(list)
    for vote in poll.votes:
        movie_name = vote.what_for.name
        if movie_name in [x.name for x in poll.options]:
            movie_votes[movie_name] += 1
            movie_voters[movie_name].append(vote.voter_nickname)
    sorted_movies= sorted(list(movie_votes.items()), key=lambda x: x[1], reverse=True)
    return "\n".join(
        [f"- **{x[0]}**: +{x[1]} [{', '.join(movie_voters[x[0]])}]" for x in sorted_movies]
    )


def add_poll_functionality(bot: Bot):

    @bot.listen('on_button_click')
    async def add_button_callback(action: discord.MessageInteraction):
        if action.component.custom_id == SUGGEST_BUTTON_ID:
            await action.response.send_modal(SuggestModal())
        else:
            await action.response.defer()

    @bot.listen('on_dropdown')
    async def vote_callback(action: discord.MessageInteraction):
        if action.component.custom_id != DROPDOWN_ID:
            await action.response.defer()
            return
        message = action.message
        poll_id = message.id
        poll: Poll = Poll.get_or_create(message_id=poll_id)[0]
        try:
            Vote.get(
                Vote.in_poll==poll_id and Vote.voter_id==action.author.id
            ).delete_instance()
        except pw.DoesNotExist: pass
        selection = action.values[0]
        voter_nickname = (action.author.nick 
            if isinstance(action.author.nick, str) 
            else action.author.name)
        if not (len(selection) == 0 or selection == ABSTENTION):
            movie = MovieOption.get(
                MovieOption.in_poll==poll_id and
                MovieOption.name==selection
            )
            Vote.create(what_for=movie.id,
                in_poll=poll_id,
                voter_id=action.author.id,
                voter_nickname=voter_nickname
            ).save()
        await action.response.edit_message(
            content=poll_model_to_vote_count(poll),
            view=poll_model_to_view(poll))

    @bot.slash_command(description="Suggestion box and voting system.")
    async def movie_poll(context: ApplicationCommandInteraction):
        await context.response.send_message(view=poll_model_to_view())
