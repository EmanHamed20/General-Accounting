from rest_framework import serializers

from accounting.models import Country, CountryCity, CountryState


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "code", "phone_code", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CountryStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryState
        fields = ["id", "country", "name", "code", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CountryCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryCity
        fields = ["id", "country", "state", "name", "postal_code", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        country = attrs.get("country") or getattr(self.instance, "country", None)
        state = attrs.get("state") if "state" in attrs else getattr(self.instance, "state", None)
        if state and country and state.country_id != country.id:
            raise serializers.ValidationError({"state": "State must belong to selected country."})
        return attrs
