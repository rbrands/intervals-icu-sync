using System.Text.Json;
using System.Text.Json.Serialization;

namespace IntervalsIcuSync.Contracts;

public static class WeekDataJson
{
    public static readonly JsonSerializerOptions DefaultOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = true,
    };

    public static WeekDataDto Deserialize(string json, JsonSerializerOptions? options = null)
    {
        var dto = JsonSerializer.Deserialize<WeekDataDto>(json, options ?? DefaultOptions);
        if (dto is null)
        {
            throw new JsonException("Failed to deserialize WeekDataDto.");
        }
        return dto;
    }

    public static string Serialize(WeekDataDto dto, JsonSerializerOptions? options = null)
    {
        return JsonSerializer.Serialize(dto, options ?? DefaultOptions);
    }
}
